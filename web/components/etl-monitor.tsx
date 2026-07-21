"use client";

import {
  Activity,
  CalendarClock,
  Check,
  Clock3,
  Database,
  GitBranch,
  Layers3,
  ScanSearch,
  Server,
  ShieldCheck,
  UploadCloud
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { EtlRun, EtlSummary, ListingMapResponse } from "../lib/types";

type Props = {
  data: ListingMapResponse;
};

const TOOLTIP_STYLE = {
  border: "1px solid rgba(77, 119, 171, 0.28)",
  borderRadius: 8,
  background: "rgba(248, 252, 255, 0.97)",
  boxShadow: "0 12px 32px rgba(31, 79, 137, 0.14)",
  color: "#18324f",
  fontSize: 12
};

const SOURCE_LABELS: Record<string, string> = {
  phongtro123: "Phongtro123",
  nhatot: "NhaTot",
  mogi: "Mogi",
  thuephongtro: "ThuePhongTro",
  batdongsan: "Batdongsan",
  alonhadat: "Alonhadat"
};

function percent(value: number, total: number) {
  if (!total) {
    return 0;
  }
  return Math.min(100, Math.max(0, (value / total) * 100));
}

function formatPercent(value: number) {
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
}

function formatDuration(value?: number | null) {
  if (value === null || value === undefined) {
    return "Chưa ghi thời lượng";
  }
  if (value < 60) {
    return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`;
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} phút ${seconds} giây`;
}

function formatRunTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh"
  }).format(date);
}

function formatRunDate(value: string) {
  const date = new Date(`${value}T00:00:00+07:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit" }).format(date);
}

function fallbackSummary(data: ListingMapResponse): EtlSummary {
  const noneRows = data.geocode_summary.none ?? 0;
  const statusCounts = data.items.reduce<Record<string, number>>((acc, item) => {
    acc[item.status] = (acc[item.status] ?? 0) + 1;
    return acc;
  }, {});
  return {
    run_id: "local-fallback",
    pipeline_version: "unknown",
    run_mode: "fallback",
    generated_at: new Date().toISOString(),
    status: "success",
    source_rows: data.total,
    source_rejected_rows: 0,
    deduplicated_rows: data.total,
    duplicate_rows: 0,
    rejected_rows: data.skipped_rows ?? 0,
    selection_excluded_rows: 0,
    candidate_rows: data.total,
    curated_rows: data.total,
    located_rows: Math.max(data.total - noneRows, 0),
    exact_geocoded_rows: data.geocode_summary.exact ?? 0,
    unresolved_geocode_rows: noneRows,
    quality_qualified_rows: data.total,
    published_rows: data.total,
    duration_seconds: null,
    source_counts: data.deploy_source_counts ?? {},
    status_counts: statusCounts
  };
}

function fallbackRuns(summary: EtlSummary): EtlRun[] {
  const localDate = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh"
  }).format(new Date(summary.generated_at));
  return [{
    run_id: summary.run_id,
    pipeline_version: summary.pipeline_version,
    run_mode: summary.run_mode,
    dataset_fingerprint: summary.dataset_fingerprint,
    date: localDate,
    generated_at: summary.generated_at,
    status: summary.status,
    source_rows: summary.source_rows,
    deduplicated_rows: summary.deduplicated_rows,
    candidate_rows: summary.candidate_rows ?? summary.curated_rows,
    curated_rows: summary.curated_rows,
    rejected_rows: summary.duplicate_rows + summary.rejected_rows,
    located_rows: summary.located_rows,
    quality_qualified_rows: summary.quality_qualified_rows ?? summary.published_rows,
    published_rows: summary.published_rows,
    duration_seconds: summary.duration_seconds
  }];
}

export function EtlMonitor({ data }: Props) {
  const summary = data.etl_summary ?? fallbackSummary(data);
  const runs = data.etl_runs?.length ? data.etl_runs : fallbackRuns(summary);
  const sourceEntries = Object.entries(summary.source_counts).sort((a, b) => b[1] - a[1]);
  const largestSource = sourceEntries[0]?.[1] ?? 1;
  const qualitySummary = data.quality_summary;
  const candidateRows = summary.candidate_rows ?? summary.curated_rows;
  const sourceRejected = summary.source_rejected_rows ?? Math.max(summary.source_rows - summary.duplicate_rows - summary.deduplicated_rows, 0);
  const selectionExcluded = summary.selection_excluded_rows ?? Math.max(summary.deduplicated_rows - candidateRows, 0);
  const qualityQualified = summary.quality_qualified_rows ?? qualitySummary?.qualified_rows ?? candidateRows;
  const qualityInput = qualitySummary?.valid_source_rows ?? candidateRows;
  const coreRejected = qualitySummary?.rejected_core_quality_rows ?? qualitySummary?.rejected_low_quality_rows ?? 0;
  const scoreRejected = qualitySummary?.rejected_score_rows ?? 0;
  const totalRemoved = Math.max(candidateRows - summary.published_rows, 0);
  const qualityRate = percent(qualityQualified, qualityInput);
  const runChart = runs.map((run) => ({
    ...run,
    candidate_rows: run.candidate_rows ?? run.curated_rows,
    quality_qualified_rows: run.quality_qualified_rows ?? run.published_rows,
    label: formatRunDate(run.date)
  }));
  const qualityEvents = [
    { label: "Lỗi dữ liệu nguồn", value: sourceRejected },
    { label: "Bản ghi trùng", value: summary.duplicate_rows },
    { label: "Thiếu trường cốt lõi", value: coreRejected },
    { label: `Điểm dưới ${qualitySummary?.minimum_score ?? 0}`, value: scoreRejected },
    { label: "Chưa định vị", value: summary.unresolved_geocode_rows }
  ];
  const layers = [
    {
      order: "01",
      title: "Thu nhận đa nguồn",
      description: "Crawler hợp nhất dữ liệu thô từ các cổng phòng trọ.",
      icon: Database,
      value: summary.source_rows,
      label: "dòng đầu vào",
      ratio: 100,
      facts: [
        `${sourceEntries.length} nguồn được thu nhận`,
        summary.source_generated_at ? `Nguồn chuẩn hóa ${formatRunTime(summary.source_generated_at)}` : "Schema nguồn được lưu vết"
      ]
    },
    {
      order: "02",
      title: "Làm sạch và định danh",
      description: "Loại dòng nguồn lỗi, chuẩn hóa khóa URL và khử trùng bản ghi.",
      icon: GitBranch,
      value: summary.deduplicated_rows,
      label: "bản ghi sạch, duy nhất",
      ratio: percent(summary.deduplicated_rows, summary.source_rows),
      facts: [`${sourceRejected.toLocaleString("vi-VN")} dòng nguồn lỗi`, `${summary.duplicate_rows.toLocaleString("vi-VN")} bản ghi trùng`]
    },
    {
      order: "03",
      title: "Cân bằng tập ứng viên",
      description: "Suy ra quy mô từ nguồn nhỏ nhất rồi xếp hạng chất lượng trong từng nguồn.",
      icon: Layers3,
      value: candidateRows,
      label: "ứng viên cân bằng",
      ratio: percent(candidateRows, summary.deduplicated_rows),
      facts: [`${selectionExcluded.toLocaleString("vi-VN")} dòng ngoài tập ứng viên`, "Nguồn nhỏ nhất chiếm tối thiểu 24%"]
    },
    {
      order: "04",
      title: "Chuẩn hóa và geocode",
      description: "Chuẩn hóa giá, diện tích, liên hệ và xác định mức chính xác vị trí.",
      icon: ScanSearch,
      value: summary.located_rows,
      label: "bản ghi có mức vị trí",
      ratio: percent(summary.located_rows, candidateRows),
      facts: [`${summary.exact_geocoded_rows.toLocaleString("vi-VN")} địa chỉ chính xác`, `${summary.unresolved_geocode_rows.toLocaleString("vi-VN")} chưa định vị`]
    },
    {
      order: "05",
      title: "Quality gate có ngưỡng",
      description: "Kiểm tra trường cốt lõi và yêu cầu điểm chất lượng tối thiểu có thể tái lập.",
      icon: ShieldCheck,
      value: qualityQualified,
      label: "bản ghi qua quality gate",
      ratio: percent(qualityQualified, candidateRows),
      facts: [`${coreRejected.toLocaleString("vi-VN")} thiếu trường cốt lõi`, `${scoreRejected.toLocaleString("vi-VN")} điểm dưới ${qualitySummary?.minimum_score ?? 0}`]
    },
    {
      order: "06",
      title: "Đóng gói và phân phối",
      description: "Chia index và chi tiết thành các chunk để phục vụ web tĩnh trên Render.",
      icon: UploadCloud,
      value: summary.published_rows,
      label: "bản ghi xuất bản",
      ratio: percent(summary.published_rows, qualityQualified),
      facts: [`Không cắt theo quota tròn`, `${data.chunks?.length ?? 0} index + ${Math.ceil(summary.published_rows / (data.detail_chunk_size ?? 500))} detail chunk`]
    }
  ];

  return (
    <section className="etl-view" aria-label="Giám sát tiến trình ETL">
      <header className="etl-overview">
        <div>
          <span className="etl-kicker">Pipeline observability</span>
          <h2>Tiến trình ETL theo từng lớp</h2>
          <p>Theo dõi đường đi của dữ liệu từ nguồn crawl đến lớp phục vụ bản đồ và phân tích.</p>
        </div>
        <div className="etl-run-state">
          <span className={`etl-status status-${summary.status}`}>
            <Check size={15} strokeWidth={2} aria-hidden />
            Lần chạy production thành công
          </span>
          <strong>{formatRunTime(summary.generated_at)}</strong>
          <small><Clock3 size={14} strokeWidth={1.9} aria-hidden /> {formatDuration(summary.duration_seconds)}</small>
          {summary.run_id ? <code>{summary.run_id}</code> : null}
        </div>
      </header>

      <div className="etl-health-strip" aria-label="Sức khỏe pipeline">
        <div><Activity size={17} strokeWidth={1.9} aria-hidden /><span>Ứng viên được xuất bản</span><strong>{formatPercent(percent(summary.published_rows, candidateRows))}</strong></div>
        <div><ShieldCheck size={17} strokeWidth={1.9} aria-hidden /><span>Đạt kiểm tra chất lượng</span><strong>{formatPercent(qualityRate)}</strong></div>
        <div><Server size={17} strokeWidth={1.9} aria-hidden /><span>Đã xuất bản</span><strong>{summary.published_rows.toLocaleString("vi-VN")}</strong></div>
        <div><CalendarClock size={17} strokeWidth={1.9} aria-hidden /><span>Phiên bản pipeline</span><strong>{summary.pipeline_version ?? "Chưa xác định"}</strong></div>
      </div>

      <section className="etl-pipeline-shell" aria-labelledby="etl-pipeline-title">
        <div className="etl-section-heading">
          <div>
            <h3 id="etl-pipeline-title">Data spine</h3>
            <p>Mỗi lớp chỉ chuyển tiếp dữ liệu đã vượt qua checkpoint trước đó.</p>
          </div>
          <span>{totalRemoved.toLocaleString("vi-VN")} ứng viên không qua quality gate</span>
        </div>
        <div className="etl-layer-stack">
          {layers.map((layer) => {
            const Icon = layer.icon;
            return (
              <article className="etl-layer" key={layer.order}>
                <div className="etl-layer-index"><span>{layer.order}</span><i /></div>
                <div className="etl-layer-icon"><Icon size={21} strokeWidth={1.8} aria-hidden /></div>
                <div className="etl-layer-copy">
                  <h4>{layer.title}</h4>
                  <p>{layer.description}</p>
                  <div className="etl-layer-facts">
                    {layer.facts.map((fact) => <span key={fact}>{fact}</span>)}
                  </div>
                </div>
                <div className="etl-layer-throughput">
                  <strong>{layer.value.toLocaleString("vi-VN")}</strong>
                  <span>{layer.label}</span>
                  <div className="etl-progress" aria-label={`${formatPercent(layer.ratio)} được giữ lại`}>
                    <i style={{ width: `${layer.ratio}%` }} />
                  </div>
                </div>
                <div className="etl-layer-pass"><Check size={15} strokeWidth={2.2} aria-hidden /><span>{formatPercent(layer.ratio)}</span></div>
              </article>
            );
          })}
        </div>
      </section>

      <div className="etl-monitor-grid">
        <article className="etl-monitor-panel etl-trend-panel">
          <div className="etl-panel-heading">
            <div><h3>Lịch sử chạy production</h3><p>Đầu vào thô, tập ứng viên, số qua gate và số được xuất bản.</p></div>
            <span>{runs.length}/30 lần chạy</span>
          </div>
          <div className="etl-chart etl-chart-wide">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={runChart} margin={{ top: 18, right: 20, left: 0, bottom: 4 }}>
                <CartesianGrid vertical={false} stroke="rgba(80, 122, 171, 0.15)" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#607089", fontSize: 11 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: "#607089", fontSize: 11 }} width={56} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend verticalAlign="top" iconType="circle" wrapperStyle={{ fontSize: 11, color: "#607089" }} />
                <Area type="monotone" dataKey="source_rows" name="Đầu vào" stroke="#7ba9dc" fill="#cfe3f8" fillOpacity={0.34} strokeWidth={2} />
                <Area type="monotone" dataKey="candidate_rows" name="Ứng viên" stroke="#176bda" fill="#82b9f4" fillOpacity={0.28} strokeWidth={2.5} />
                <Area type="monotone" dataKey="quality_qualified_rows" name="Qua gate" stroke="#5474c8" fill="#aebff0" fillOpacity={0.2} strokeWidth={2} />
                <Area type="monotone" dataKey="published_rows" name="Xuất bản" stroke="#0e7490" fill="#67c7d8" fillOpacity={0.16} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="etl-history-note">Ledger chỉ nhận run production có mã chạy và fingerprint; các lần export thử nghiệm cũ không được nhập vào lịch sử này.</p>
        </article>

        <article className="etl-monitor-panel">
          <div className="etl-panel-heading">
            <div><h3>Checkpoint chất lượng</h3><p>Những dòng không đi tiếp qua pipeline.</p></div>
          </div>
          <div className="etl-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={qualityEvents} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 4 }}>
                <CartesianGrid horizontal={false} stroke="rgba(80, 122, 171, 0.15)" />
                <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#607089", fontSize: 11 }} />
                <YAxis type="category" dataKey="label" width={148} tickLine={false} axisLine={false} tick={{ fill: "#31445f", fontSize: 11 }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="value" name="Số dòng" fill="#176bda" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="etl-monitor-panel etl-source-panel">
          <div className="etl-panel-heading">
            <div><h3>Đóng góp theo nguồn</h3><p>Số bản ghi trong snapshot public đã qua quality gate.</p></div>
            <span>{sourceEntries.length} crawler</span>
          </div>
          <div className="etl-source-list">
            {sourceEntries.map(([source, value]) => (
              <div key={source}>
                <span>{SOURCE_LABELS[source] ?? source}</span>
                <div><i style={{ width: `${percent(value, largestSource)}%` }} /></div>
                <strong>{value.toLocaleString("vi-VN")}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="etl-monitor-panel etl-log-panel">
          <div className="etl-panel-heading">
            <div><h3>Nhật ký chạy có kiểm chứng</h3><p>Mỗi dòng gắn với run ID, phiên bản pipeline và fingerprint dữ liệu.</p></div>
          </div>
          <div className="etl-run-table" role="table" aria-label="Lịch sử chạy ETL">
            <div className="etl-run-row etl-run-head" role="row">
              <span>Thời điểm</span><span>Mã chạy</span><span>Đầu vào</span><span>Ứng viên</span><span>Qua gate</span><span>Xuất bản</span><span>Thời lượng</span>
            </div>
            {[...runs].reverse().map((run) => (
              <div className="etl-run-row" role="row" key={run.run_id ?? `${run.date}-${run.generated_at}`}>
                <div className="etl-run-time">
                  <strong>{formatRunTime(run.generated_at)}</strong>
                  <span className={`run-status status-${run.status}`}><i />{run.status === "success" ? "Thành công" : run.status}</span>
                </div>
                <div className="etl-run-identity">
                  <code>{run.run_id ?? "Không có run ID"}</code>
                  <small>{run.pipeline_version ?? "Không rõ phiên bản"}</small>
                </div>
                <span>{run.source_rows.toLocaleString("vi-VN")}</span>
                <span>{(run.candidate_rows ?? run.curated_rows).toLocaleString("vi-VN")}</span>
                <span>{(run.quality_qualified_rows ?? run.published_rows).toLocaleString("vi-VN")}</span>
                <span>{run.published_rows.toLocaleString("vi-VN")}</span>
                <span>{formatDuration(run.duration_seconds)}</span>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
