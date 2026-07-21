import { readFile } from "node:fs/promises";
import path from "node:path";

const dataRoot = path.resolve("public/data");
const manifestPath = path.join(dataRoot, "listings-map.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

const canonicalProvinces = new Set([
  "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu", "Bắc Ninh",
  "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước", "Bình Thuận", "Cà Mau", "Cần Thơ",
  "Cao Bằng", "Đà Nẵng", "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp",
  "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang",
  "Hòa Bình", "Hồ Chí Minh", "Huế", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
  "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận",
  "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
  "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Tiền Giang",
  "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái"
]);

if (!Array.isArray(manifest.chunks) || manifest.chunks.length === 0) {
  throw new Error("Static manifest has no index chunks");
}
if (Number(manifest.total) < 50_000) {
  throw new Error(`Static manifest only contains ${manifest.total} rows`);
}
if (Number(manifest.total) > 55_000) {
  throw new Error(`Static manifest contains unexpectedly many public rows: ${manifest.total}`);
}
if (!manifest.quality_summary?.enabled) {
  throw new Error("Static manifest quality gate is not enabled");
}
if (Number(manifest.quality_summary.published_rows) !== Number(manifest.total)) {
  throw new Error("Quality summary published count does not match static manifest total");
}
const candidateRows = Number(manifest.quality_summary.input_rows);
const removedCandidateRows = candidateRows - Number(manifest.total);
const minimumQualityScore = Number(manifest.quality_summary.minimum_score);
if (candidateRows < 55_000 || candidateRows > 60_000) {
  throw new Error(`Balanced candidate pool is outside the expected data-derived range: ${candidateRows}`);
}
if (candidateRows % 1_000 === 0 || Number(manifest.total) % 1_000 === 0) {
  throw new Error("Candidate and publication counts must be produced by data rules, not round presentation quotas");
}
if (removedCandidateRows < 4_000 || removedCandidateRows > 7_000) {
  throw new Error(`Quality gate removed an unexpected number of candidates: ${removedCandidateRows}`);
}
if (minimumQualityScore !== 68) {
  throw new Error(`Unexpected publication quality threshold: ${minimumQualityScore}`);
}
if (Number(manifest.quality_summary.qualified_rows) !== Number(manifest.total) || Number(manifest.quality_summary.trimmed_rows) !== 0) {
  throw new Error("Every row that passes the score-based quality gate must be published without a round-number cap");
}
if (!manifest.etl_summary || !Array.isArray(manifest.etl_runs) || manifest.etl_runs.length === 0) {
  throw new Error("Static manifest has no ETL monitoring metadata");
}
if (Number(manifest.etl_summary.published_rows) !== Number(manifest.total)) {
  throw new Error("ETL published row count does not match static manifest total");
}
if (Number(manifest.etl_summary.candidate_rows) !== candidateRows || Number(manifest.etl_summary.quality_qualified_rows) !== Number(manifest.total)) {
  throw new Error("ETL layer counts do not match the quality summary");
}
if (Number(manifest.etl_summary.source_rows) < Number(manifest.etl_summary.deduplicated_rows) || Number(manifest.etl_summary.deduplicated_rows) < candidateRows) {
  throw new Error("ETL layer counts are not monotonically decreasing");
}
if (!manifest.etl_summary.run_id || !manifest.etl_summary.dataset_fingerprint || manifest.etl_summary.pipeline_version !== "production-quality-v3") {
  throw new Error("ETL summary is missing production provenance");
}
if (manifest.etl_runs.some((run) => !run.run_id || !run.dataset_fingerprint || run.pipeline_version !== "production-quality-v3")) {
  throw new Error("ETL history contains an unverified or non-production run");
}

const ids = new Set();
const detailPaths = new Set();
const invalidProvinces = new Set();
const sourceRows = new Map();
const indexById = new Map();
const realImageIds = new Set();
let indexRows = 0;
let imageRows = 0;
let noImageRows = 0;
let contactRows = 0;

for (const chunkPath of manifest.chunks) {
  const payload = JSON.parse(await readFile(path.join(dataRoot, chunkPath), "utf8"));
  for (const item of payload.items ?? []) {
    indexRows += 1;
    if (!item.id || ids.has(item.id)) {
      throw new Error(`Missing or duplicate listing id: ${item.id}`);
    }
    ids.add(item.id);
    indexById.set(item.id, item);
    sourceRows.set(item.source_name, (sourceRows.get(item.source_name) ?? 0) + 1);
    if (item.province && !canonicalProvinces.has(item.province)) {
      invalidProvinces.add(item.province);
    }
    if (!item.detail_path) {
      throw new Error(`Listing ${item.id} has no lazy detail path`);
    }
    const hasRealImage = /^https?:\/\//i.test(item.thumbnail_url ?? "") && !/(?:thumb_default|no[-_]image|placeholder|default[-_]image)/i.test(item.thumbnail_url);
    if (hasRealImage) realImageIds.add(item.id);
    imageRows += hasRealImage ? 1 : 0;
    noImageRows += hasRealImage ? 0 : 1;
    const hasContact = item.has_direct_contact || item.has_contact_name;
    contactRows += hasContact ? 1 : 0;
    if (indexRows <= 500 && (!hasRealImage || !hasContact)) {
      throw new Error(`Top-ranked listing ${item.id} must include both a real image and contact information`);
    }
    if (Number(item.publication_quality_score) < minimumQualityScore) {
      throw new Error(`Listing ${item.id} has a low publication quality score`);
    }
    if (Number(item.price_value) < 300_000 || Number(item.price_value) > 30_000_000) {
      throw new Error(`Listing ${item.id} has an invalid public price`);
    }
    if (Number(item.area_m2) < 6 || Number(item.area_m2) > 300) {
      throw new Error(`Listing ${item.id} has an invalid public area`);
    }
    if (!item.province || !item.district || (!item.street_address && !item.full_address)) {
      throw new Error(`Listing ${item.id} has an incomplete public address`);
    }
    detailPaths.add(item.detail_path);
  }
}

if (indexRows !== Number(manifest.total)) {
  throw new Error(`Manifest total ${manifest.total} does not match ${indexRows} index rows`);
}
if (invalidProvinces.size) {
  throw new Error(`Invalid provinces: ${[...invalidProvinces].slice(0, 10).join(", ")}`);
}
for (const source of ["phongtro123", "nhatot", "mogi"]) {
  if ((sourceRows.get(source) ?? 0) < 10_000) {
    throw new Error(`Source ${source} is under-represented: ${sourceRows.get(source) ?? 0}`);
  }
}

let detailRows = 0;
const detailIds = new Set();
for (const detailPath of detailPaths) {
  const payload = JSON.parse(await readFile(path.join(dataRoot, detailPath), "utf8"));
  for (const item of payload.items ?? []) {
    detailRows += 1;
    if (!ids.has(item.id)) {
      throw new Error(`Detail row has unknown listing id: ${item.id}`);
    }
    if (detailIds.has(item.id)) {
      throw new Error(`Duplicate detail row: ${item.id}`);
    }
    detailIds.add(item.id);
    if (String(item.contact_zalo_url ?? "").includes("0909316890")) {
      throw new Error(`Source hotline leaked into Zalo contact for ${item.id}`);
    }
    if (Object.hasOwn(item, "content_hash")) {
      throw new Error(`Public detail exposes content_hash for ${item.id}`);
    }
    const indexItem = indexById.get(item.id);
    const hasDescription = String(item.description_clean ?? "").trim().length >= 80;
    if (!hasDescription && !indexItem?.has_direct_contact && !indexItem?.has_contact_name && !realImageIds.has(item.id)) {
      throw new Error(`Public detail ${item.id} has no useful image, contact, or description`);
    }
    if (!/^https?:\/\//i.test(item.canonical_url ?? "")) {
      throw new Error(`Public detail has no canonical URL for ${item.id}`);
    }
  }
}

if (detailRows !== indexRows) {
  throw new Error(`Detail rows ${detailRows} do not match index rows ${indexRows}`);
}

console.log(JSON.stringify({
  status: "ok",
  indexRows,
  detailRows,
  indexChunks: manifest.chunks.length,
  detailChunks: detailPaths.size,
  provinces: manifest.available_provinces?.length ?? 0,
  etlRuns: manifest.etl_runs.length,
  imageRows,
  noImageRows,
  contactRows,
  sourceRows: Object.fromEntries(sourceRows),
  candidateRows,
  removedCandidateRows,
  minimumQualityScore,
  runId: manifest.etl_summary.run_id,
  rejectedLowQuality: manifest.quality_summary.rejected_low_quality_rows,
  trimmedRows: manifest.quality_summary.trimmed_rows
}));
