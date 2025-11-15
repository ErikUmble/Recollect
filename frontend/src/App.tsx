import React, { useState } from 'react';
import './App.css';
import DirectoryBrowser from './components/DirectoryBrowser';
import SearchResult from './components/SearchResult';

type Result = { path: string; excerpt: string };

const API_BASE = 'http://127.0.0.1:5000';

const App: React.FC = () => {
  const [directoryPath, setDirectoryPath] = useState('');
  const [browserOpen, setBrowserOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<Result[]>([]);
  const [logs, setLogs] = useState<{ text: string; type: 'info' | 'success' | 'error' }[]>([]);
  const [status, setStatus] = useState('Idle');

  // log helper
  const log = (text: string, type: 'info' | 'success' | 'error' = 'info') => {
    const timestamp = `[${new Date().toLocaleTimeString()}] ${text}`;
    setLogs((prev) => [{ text: timestamp, type }, ...prev]);
  };

  // set directory on backend
  const setDirectory = async (path: string) => {
    if (!path) return;
    setStatus('Setting path...');
    try {
      const resp = await fetch(`${API_BASE}/api/set-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      if (!resp.ok) throw new Error('Failed to set path');
      log(`Directory set: ${path}`, 'success');
      setDirectoryPath(path);
      setStatus('Idle');
      setBrowserOpen(false);
    } catch (e: any) {
      log(e.message, 'error');
      setStatus('Error');
    }
  };

  // search backend
  const search = async (q: string) => {
    if (!q) {
      log('Please enter search terms', 'error');
      return;
    }
    if (!directoryPath) {
      log('Please select a directory first', 'error');
      return;
    }
    setStatus('Searching');
    try {
      const resp = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q, path: directoryPath }),
      });
      if (!resp.ok) throw new Error('Search failed');
      const data = await resp.json();
      setResults(data.results || []);
      log(`Search returned ${(data.results || []).length} results`, 'success');
      setStatus('Idle');
    } catch (e: any) {
      log(e.message, 'error');
      setStatus('Error');
    }
  };

  const escapeHtml = (s: string) =>
    String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  return (
    <div className="frame">
      <header>
        <div className="logo">RECOLLECT</div>
        <div className="subtitle">retro assistant — local, private, fast</div>
        <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted)' }}>
          Status: <span>{status}</span>
        </div>
      </header>

      <aside className="sidebar">
        <div>
          <button className="btn primary" onClick={() => setBrowserOpen(true)}>
            {directoryPath ? 'Change Directory' : 'Choose Directory'}
          </button>
          {directoryPath && (
            <div
              style={{
                fontSize: 11,
                marginTop: 6,
                color: 'var(--accent)',
                fontFamily: "'Inconsolata', monospace",
              }}
            >
              {directoryPath}
            </div>
          )}
        </div>
      </aside>

      <main className="main">
        <div className="searchbar">
          <input
            className="search-input"
            type="search"
            placeholder="Search your recollections..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search(searchQuery.trim())}
          />
          <button className="btn primary" onClick={() => search(searchQuery.trim())}>
            Search
          </button>
        </div>

        <div className="results" role="region" aria-live="polite">
        {results.length ? (
          results.map((r, idx) => <SearchResult key={idx} result={r} />)
          ) : (
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>No results yet.</div>
          )}
        </div>

        <div className="console">
          {logs.map((logEntry, idx) => (
            <div
              key={idx}
              className={`log ${
                logEntry.type === 'success' ? 'success' : logEntry.type === 'error' ? 'error' : ''
              }`}
            >
              {logEntry.text}
            </div>
          ))}
        </div>
      </main>

      <footer>
        <div>Local-only mode supported</div>
        <div style={{ fontFamily: "'PressStart2P', monospace", color: 'var(--accent)', fontSize: 10 }}>
          v0.9 RETRO
        </div>
      </footer>

      {/* Directory Browser Modal */}
      <DirectoryBrowser
        open={browserOpen}
        currentPath={directoryPath || '.'}
        onClose={() => setBrowserOpen(false)}
        onSelect={(path) => setDirectory(path)}
        apiBase={API_BASE}
        log={log}
      />
    </div>
  );
};

export default App;
