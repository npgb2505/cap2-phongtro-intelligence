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
    generated_at: new Date().toISOString(),
    status: "success",
    source_rows: data.total,
    deduplicated_rows: data.total,
    duplicate_rows: 0,
    rejected_rows: data.skipped_rows ?? 0,
    curated_rows: data.total,
    located_rows: Math.max(data.total - noneRows, 0),
    exact_geocoded_rows: data.geocode_summary.exact ?? 0,
    unresolved_geocode_rows: noneRows,
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
    date: localDate,
    generated_at: summary.generated_at,
    status: summary.status,
    source_rows: summary.source_rows,
    curated_rows: summary.curated_rows,
    rejected_rows: summary.duplicate_rows + summary.rejected_rows,
    located_rows: summary.located_rows,
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
  const totalRemoved = Math.max(summary.source_rows - summary.published_rows, 0);
  const curationRejected = Math.max(summary.source_rows - summary.duplicate_rows - summary.curated_rows, 0);
  const qualityQualified = qualitySummary?.qualified_rows ?? summary.curated_rows;
  const qualityInput = qualitySummary?.valid_source_rows ?? summary.curated_rows;
  const qualityRate = percent(qualityQualified, qualityInput);
  const publicCapLabel = `${Math.round(summary.published_rows / 1000)}k`;
  const runChart = runs.map((run) => ({
    ...run,
    label: formatRunDate(run.date)
  }));
  const qualityEvents = [
    { label: "Bản ghi trùng", value: summary.duplicate_rows },
    { label: "Thiếu dữ liệu", value: qualitySummary?.rejected_low_quality_rows ?? summary.rejected_rows },
    { label: `Ngoài top ${publicCapLabel}`, value: qualitySummary?.trimmed_rows ?? 0 },
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
      facts: [`${sourceEntries.length} nguồn được xuất bản`, "Schema nguồn được lưu vết"]
    },
    {
      order: "02",
      title: "Staging và định danh",
      description: "Chuẩn hóa khóa nguồn, URL và loại bỏ bản ghi lặp.",
      icon: GitBranch,
      value: summary.deduplicated_rows,
      label: "dòng duy nhất",
      ratio: percent(summary.deduplicated_rows, summary.source_rows),
      facts: [`${summary.duplicate_rows.toLocaleString("vi-VN")} dòng trùng`, "ID ổn định theo canonical URL"]
    },
    {
      order: "03",
      title: "Biến đổi và chuẩn hóa",
      description: "Làm sạch giá, diện tích, địa chỉ, liên hệ và tiện ích.",
      icon: Layers3,
      value: summary.curated_rows,
      label: "bản ghi đạt chuẩn",
      ratio: percent(summary.curated_rows, summary.deduplicated_rows),
      facts: [`${curationRejected.toLocaleString("vi-VN")} dòng lỗi schema`, "Giá, diện tích và địa chỉ đã chuẩn hóa"]
    },
    {
      order: "04",
      title: "Chất lượng và geocode",
      description: "Xác minh số nhà, tuyến đường và hạ cấp vị trí khi thiếu dữ liệu.",
      icon: ScanSearch,
      value: summary.located_rows,
      label: "bản ghi có mức vị trí",
      ratio: percent(summary.located_rows, summary.curated_rows),
      facts: [`${summary.exact_geocoded_rows.toLocaleString("vi-VN")} địa chỉ chính xác`, `${summary.unresolved_geocode_rows.toLocaleString("vi-VN")} chưa định vị`]
    },
    {
      order: "05",
      title: "Quality gate và phân phối",
      description: "Giữ trường cốt lõi rồi ưu tiên liên hệ, ảnh và mô tả khi xếp hạng.",
      icon: UploadCloud,
      value: summary.published_rows,
      label: "bản ghi xuất bản",
      ratio: percent(summary.published_rows, summary.curated_rows),
      facts: [`${qualityQualified.toLocaleString("vi-VN")} tin đủ điều kiện`, `${data.chunks?.length ?? 0} index + ${Math.ceil(summary.published_rows / (data.detail_chunk_size ?? 500))} detail chunk`]
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
            Lần chạy gần nhất thành công
          </span>
          <strong>{formatRunTime(summary.generated_at)}</strong>
          <small><Clock3 size={14} strokeWidth={1.9} aria-hidden /> {formatDuration(summary.duration_seconds)}</small>
        </div>
      </header>

      <div className="etl-health-strip" aria-label="Sức khỏe pipeline">
        <div><Activity size={17} strokeWidth={1.9} aria-hidden /><span>Tỷ lệ xuất bản</span><strong>{formatPercent(percent(summary.published_rows, summary.source_rows))}</strong></div>
        <div><ShieldCheck size={17} strokeWidth={1.9} aria-hidden /><span>Đạt kiểm tra chất lượng</span><strong>{formatPercent(qualityRate)}</strong></div>
        <div><Server size={17} strokeWidth={1.9} aria-hidden /><span>Đã xuất bản</span><strong>{summary.published_rows.toLocaleString("vi-VN")}</strong></div>
        <div><CalendarClock size={17} strokeWidth={1.9} aria-hidden /><span>Lịch tự động</span><strong>CN, 10:17</strong></div>
      </div>

      <section className="etl-pipeline-shell" aria-labelledby="etl-pipeline-title">
        <div className="etl-section-heading">
          <div>
            <h3 id="etl-pipeline-title">Data spine</h3>
            <p>Mỗi lớp chỉ chuyển tiếp dữ liệu đã vượt qua checkpoint trước đó.</p>
          </div>
          <span>{totalRemoved.toLocaleString("vi-VN")} dòng được loại khỏi luồng</span>
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
            <div><h3>Nhịp chạy theo ngày</h3><p>Đầu vào, sau chuẩn hóa và số bản ghi xuất bản.</p></div>
            <span>{runs.length}/30 ngày có dữ liệu</span>
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
                <Area type="monotone" dataKey="curated_rows" name="Đạt chuẩn" stroke="#176bda" fill="#82b9f4" fillOpacity={0.28} strokeWidth={2.5} />
                <Area type="monotone" dataKey="published_rows" name="Xuất bản" stroke="#0e7490" fill="#67c7d8" fillOpacity={0.16} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {runs.length === 1 ? <p className="etl-history-note">Lịch sử bắt đầu từ snapshot này. Mỗi lần export tiếp theo sẽ tự nối thêm một điểm theo ngày.</p> : null}
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
            <div><h3>Nhật ký chạy</h3><p>Tối đa 30 mốc gần nhất được đóng gói cùng snapshot.</p></div>
          </div>
          <div className="etl-run-table" role="table" aria-label="Lịch sử chạy ETL">
            <div className="etl-run-row etl-run-head" role="row">
              <span>Thời điểm</span><span>Trạng thái</span><span>Đầu vào</span><span>Đạt chuẩn</span><span>Xuất bản</span><span>Thời lượng</span>
            </div>
            {[...runs].reverse().map((run) => (
              <div className="etl-run-row" role="row" key={`${run.date}-${run.generated_at}`}>
                <strong>{formatRunTime(run.generated_at)}</strong>
                <span className={`run-status status-${run.status}`}><i />{run.status === "success" ? "Thành công" : run.status}</span>
                <span>{run.source_rows.toLocaleString("vi-VN")}</span>
                <span>{run.curated_rows.toLocaleString("vi-VN")}</span>
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
