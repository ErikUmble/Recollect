import React, { useState, useEffect } from 'react';
import './App.css';

type Dir = { name: string; full: string };
type Result = { path: string; excerpt: string };

const API_BASE = 'http://127.0.0.1:5000';

const App: React.FC = () => {
  const [results, setResults] = useState<Result[]>([]);
  const [logs, setLogs] = useState<{ text: string; type: 'info' | 'success' | 'error' }[]>([]);
  const [status, setStatus] = useState('Idle');
  const [searchQuery, setSearchQuery] = useState('');
  const [directoryPath, setDirectoryPath] = useState('');
  const [browserOpen, setBrowserOpen] = useState(false);
  const [currentBrowserPath, setCurrentBrowserPath] = useState('.');
  const [dirs, setDirs] = useState<Dir[]>([]);

  const log = (text: string, type: 'info' | 'success' | 'error' = 'info') => {
    const timestamp = `[${new Date().toLocaleTimeString()}] ${text}`;
    setLogs((prev) => [{ text: timestamp, type }, ...prev]);
  };

  const fetchDirs = async (path: string) => {
    try {
      const resp = await fetch(`${API_BASE}/api/list-dirs?path=${encodeURIComponent(path)}`);
      const data = await resp.json();
      setDirs(data.dirs || []);
      setCurrentBrowserPath(path);
    } catch (e: any) {
      log(e.message, 'error');
    }
  };

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

  const goUp = () => {
    const parts = currentBrowserPath.split(/[/\\]/);
    if (parts.length > 1) {
      const parent = parts.slice(0, -1).join('/');
      fetchDirs(parent || '.');
    }
  };

  useEffect(() => {
    if (browserOpen) {
      fetchDirs(currentBrowserPath);
    }
  }, [browserOpen]);

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
            results.map((it, idx) => (
              <div key={idx} className="result">
                <div className="filename">{escapeHtml(it.path || 'unknown')}</div>
                <div className="excerpt">{escapeHtml(it.excerpt || '').slice(0, 500)}</div>
              </div>
            ))
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
      {browserOpen && (
        <div className="modal">
          <div className="modal-content">
            <div className="modal-header">
              <span>Choose Directory</span>
              <button className="btn" onClick={() => setBrowserOpen(false)}>
                X
              </button>
            </div>
            <div className="modal-body">
              <button className="btn" onClick={goUp}>
                .. (Up)
              </button>
              {dirs.length === 0 && <div style={{ color: 'var(--muted)' }}>No subdirectories</div>}
              {dirs.map((d) => (
                <div key={d.full} className="dir-item">
                  <button className="btn" onClick={() => fetchDirs(d.full)}>
                    {d.name}
                  </button>
                  <button className="btn primary" onClick={() => setDirectory(d.full)}>
                    Select
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
