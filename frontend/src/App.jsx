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

function KeyValuePanel({ title, rows }) {
  return (
    <section className="panel data-panel">
      <h2>{title}</h2>
      <MetricTable rows={rows} />
    </section>
  );
}

function PointsPanel({ points }) {
  return (
    <section className="panel data-panel">
      <h2>Dashboard Result</h2>
      <ul className="point-list">
        {(points?.length ? points : ['No result points available.']).map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
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
  const displayMode = page.display_mode ?? 'table';
  const showGraph = displayMode === 'graph' || displayMode === 'both';
  const showTable = displayMode === 'table' || displayMode === 'both' || !plotUrl;

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
        <KeyValuePanel title="Input Config" rows={page.input_rows} />
        <KeyValuePanel title="Paper Target" rows={page.paper_rows} />
        <PointsPanel points={page.result_points} />
        <ArtifactLinks page={page} baseUrl={baseUrl} />
      </section>

      <section className={`visual-grid ${showGraph && !showTable ? 'single-visual' : ''}`}>
        {showTable && (
          <section className="panel table-panel">
            <div className="section-heading">
              <Table2 size={18} />
              <h2>Table</h2>
            </div>
            <MetricTable rows={page.table_rows} />
          </section>
        )}
        {showGraph && (
          <section className="panel plot-panel">
            <div className="section-heading">
              <ImageIcon size={18} />
              <h2>Graph</h2>
            </div>
            {plotUrl ? <img src={plotUrl} alt={`${page.title} graph`} /> : <div className="missing-plot">No graph output found.</div>}
          </section>
        )}
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
