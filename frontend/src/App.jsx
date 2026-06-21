import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  BookOpen,
  CircuitBoard,
  Download,
  FileArchive,
  Filter,
  Gauge,
  GitCompare,
  Image as ImageIcon,
  LineChart,
  RefreshCw,
  Settings2,
  Sigma,
  SlidersHorizontal,
  Table2,
  Waves,
} from 'lucide-react';
import MetricTable from '../components/MetricTable.jsx';
import { DEFAULT_API_BASE, apiGet, artifactUrl } from './api.js';

const ICONS = {
  'plant-setup': Settings2,
  'model-equations': BookOpen,
  controller: CircuitBoard,
  'sysid-setup': Sigma,
  'logging-validation': LineChart,
  'excitation-validation': Waves,
  'noise-lpf-validation': Filter,
  'drift-validation': GitCompare,
  'retuning-validation': SlidersHorizontal,
  'export-report': FileArchive,
};

function StatusBadge({ status }) {
  return <span className={`status-badge ${String(status || 'missing').toLowerCase()}`}>{status || 'missing'}</span>;
}

function formatJson(value) {
  if (value === null || value === undefined) return 'No data';
  return JSON.stringify(value, null, 2);
}

function resultOverview(result) {
  if (!result || typeof result !== 'object') return {};
  const keys = [
    'validation',
    'plant_id',
    'status',
    'pass_fail_status',
    'trend_status',
    'best_Tlog_ms',
    'best_RMSE_theta',
    'skipped_profiles',
    'expected_summary',
  ];
  return Object.fromEntries(keys.filter((key) => key in result).map((key) => [key, result[key]]));
}

function JsonPanel({ title, value }) {
  return (
    <section className="panel data-panel">
      <h2>{title}</h2>
      <pre className="json-block">{formatJson(value)}</pre>
    </section>
  );
}

function ArtifactLinks({ page, baseUrl }) {
  const files = page.output_files ?? {};
  const entries = [
    ['CSV download', files.csv, Download],
    ['Plot', files.plot, ImageIcon],
    ['JSON summary', files.json, FileArchive],
  ];

  return (
    <section className="panel link-panel">
      <h2>Outputs</h2>
      <div className="result-actions">
        {entries.map(([label, file, Icon]) => {
          const href = file?.available ? artifactUrl(baseUrl, file.url) : null;
          if (!href) {
            return (
              <span className="icon-link disabled-link" key={label}>
                <Icon size={16} /> {label}
              </span>
            );
          }
          return (
            <a className="icon-link" href={href} target="_blank" rel="noreferrer" key={label}>
              <Icon size={16} /> {label}
            </a>
          );
        })}
      </div>
    </section>
  );
}

function PageView({ page, baseUrl }) {
  const plotFile = page.output_files?.plot;
  const plotUrl = plotFile?.available ? artifactUrl(baseUrl, plotFile.url) : null;
  const overview = resultOverview(page.dashboard_result);

  return (
    <div className="dashboard-page">
      <section className="summary-strip">
        <div className="panel formula-panel">
          <h2>Formula</h2>
          <p className="formula">{page.formula}</p>
        </div>
        <div className="panel status-panel">
          <h2>Pass/Fail</h2>
          <StatusBadge status={page.pass_fail} />
          <p>{page.trend_status}</p>
        </div>
      </section>

      <section className="detail-grid">
        <JsonPanel title="Input Config" value={page.input_config} />
        <JsonPanel title="Paper Target" value={page.paper_target} />
        <section className="panel data-panel">
          <h2>Dashboard Result</h2>
          {Object.keys(overview).length > 0 ? <MetricTable rows={overview} /> : <pre className="json-block">{formatJson(page.dashboard_result)}</pre>}
        </section>
        <ArtifactLinks page={page} baseUrl={baseUrl} />
      </section>

      <section className="visual-grid">
        <section className="panel table-panel">
          <div className="section-heading">
            <Table2 size={18} />
            <h2>Table</h2>
          </div>
          <MetricTable rows={page.table_rows} />
        </section>
        <section className="panel plot-panel">
          <div className="section-heading">
            <ImageIcon size={18} />
            <h2>Plot</h2>
          </div>
          {plotUrl ? <img src={plotUrl} alt={`${page.title} plot`} /> : <div className="missing-plot">No plot output found.</div>}
        </section>
      </section>
    </div>
  );
}

function ErrorBanner({ message }) {
  if (!message) return null;
  return <div className="error-banner">{message}</div>;
}

export default function App() {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_API_BASE);
  const [status, setStatus] = useState('checking');
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [activePageId, setActivePageId] = useState('plant-setup');

  const pages = dashboard?.pages ?? [];
  const activePage = useMemo(
    () => pages.find((page) => page.id === activePageId) ?? pages[0],
    [activePageId, pages],
  );

  async function refreshDashboard() {
    try {
      setStatus('checking');
      const [health, payload] = await Promise.all([apiGet(baseUrl, '/health'), apiGet(baseUrl, '/dashboard/outputs')]);
      setStatus(health.status === 'ok' ? 'online' : 'unknown');
      setDashboard(payload);
      if (payload.pages?.length && !payload.pages.some((page) => page.id === activePageId)) {
        setActivePageId(payload.pages[0].id);
      }
      setError('');
    } catch (err) {
      setStatus('offline');
      setError(err.message);
    }
  }

  useEffect(() => {
    refreshDashboard();
  }, []);

  const ActiveIcon = ICONS[activePage?.id] ?? Activity;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <Gauge size={26} />
          <div>
            <strong>R2R Validation</strong>
            <span>Output dashboard</span>
          </div>
        </div>
        <nav className="page-nav">
          {pages.map((page) => {
            const Icon = ICONS[page.id] ?? Activity;
            return (
              <button
                className={activePage?.id === page.id ? 'active' : ''}
                type="button"
                onClick={() => setActivePageId(page.id)}
                key={page.id}
              >
                <Icon size={18} />
                <span>{page.title}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="title-block">
            <ActiveIcon size={24} />
            <div>
              <h1>{activePage?.title ?? 'Dashboard'}</h1>
              <span className={`status-pill ${status}`}>{status}</span>
            </div>
          </div>
          <div className="api-controls">
            <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} aria-label="API base URL" />
            <button className="icon-button" type="button" onClick={refreshDashboard} title="Refresh output files">
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        <ErrorBanner message={error} />

        {activePage ? (
          <PageView page={activePage} baseUrl={baseUrl} />
        ) : (
          <section className="panel empty-panel">No dashboard output loaded.</section>
        )}
      </main>
    </div>
  );
}
