import React, { useState } from 'react';
import './App.css';
import DirectoryBrowser from './components/DirectoryBrowser';
import { SearchResult, type Result } from './components/SearchResult';
import AISummary from './components/AISummary';

// get API_BASE from environment variable or default
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000';
console.log('Using API_BASE:', API_BASE);

const IS_DEMO = import.meta.env.VITE_DEMO_MODE === 'true';
const PATH = import.meta.env.VITE_DEMO_PATH || '';

const App: React.FC = () => {
  const [directoryPath, setDirectoryPath] = useState(IS_DEMO ? '' : PATH);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<Result[]>([]);
  const [logs, setLogs] = useState<{ text: string; type: 'info' | 'success' | 'error' }[]>([]);
  const [aiSummary, setAISummary] = useState('');
  const [pendingStatus, setPendingStatus] = useState<string[]>([]);

  console.log('Current directoryPath:', directoryPath);

  // log helper
  const log = (text: string, type: 'info' | 'success' | 'error' = 'info') => {
    const timestamp = `[${new Date().toLocaleTimeString()}] ${text}`;
    setLogs((prev) => [{ text: timestamp, type }, ...prev]);
  };

  const appendStatus = (status: string) => {
    setPendingStatus((prev) => [...prev, status]);
  }
  const removeStatus = (status: string) => {
    setPendingStatus((prev) => prev.filter((s) => s !== status));
  }
  const status = pendingStatus.length > 0 ? pendingStatus[pendingStatus.length - 1] : 'Idle';

  const searchAndPrompt = async (query: string) => {
      if (!query) return;

      // Run both async functions in parallel
      try {
        appendStatus('Searching');
        appendStatus('Generating AI Summary');
        const [searchResults, promptAnswer] = await Promise.all([
          search(query),         // your existing search function
          prompt(query), // new async prompt
        ]);

        console.log('Prompt result:', promptAnswer);
        setAISummary(promptAnswer);
      } catch (err) {
        console.error(err);
        log(err.message, 'error');
        appendStatus('Error');
      } finally {
        removeStatus('Searching');
        removeStatus('Generating AI Summary');
      }
    }

  // set directory on backend
  const setDirectory = async (path: string) => {
    if (!path) return;
    appendStatus('Setting Directory');
    try {
      const resp = await fetch(`${API_BASE}/api/set-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      if (!resp.ok) throw new Error('Failed to set path');
      log(`Directory set: ${path}`, 'success');
      setDirectoryPath(path);
      removeStatus('Setting Directory');
      setBrowserOpen(false);
    } catch (e: any) {
      log(e.message, 'error');
      appendStatus('Error');
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
    appendStatus('Searching');
    try {
      const resp = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, path: directoryPath }),
      });
      if (!resp.ok) throw new Error('Search failed');
      const data = await resp.json();
      setResults(data.results || []);
      log(`Search returned ${(data.results || []).length} results`, 'success');
      removeStatus('Searching');
    } catch (e: any) {
      log(e.message, 'error');
      appendStatus('Error');
    }
  };

  // prompt backend
  const prompt = async (q: string) => {
    if (!q) {
      log('Please enter a prompt', 'error');
      return;
    }
    if (!directoryPath) {
      log('Please select a directory first', 'error');
      return;
    }
    appendStatus('Generating AI Summary');
    try {
      const resp = await fetch(`${API_BASE}/api/agent/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: q, path: directoryPath }),
      });
      if (!resp.ok) throw new Error('Prompt failed');
      const data = await resp.json();
      log(`AI Summary generated`, 'success');
      removeStatus('Generating AI Summary');
      return data.response || '';
    } catch (e: any) {
      log(e.message, 'error');
      appendStatus('Error');
      return '';
    }
  }

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
          <button
            className="btn primary"
            onClick={() => setBrowserOpen(true)}
            disabled={!IS_DEMO}
            style={{
              cursor: IS_DEMO ? 'pointer' : 'not-allowed',
              boxShadow: !IS_DEMO ? 'none' : undefined,
            }}
            title={IS_DEMO ? '' : 'Directory selection disabled while not in demo mode'}
          >
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
        <AISummary summary={aiSummary} />
      </aside>

      <main className="main">
        <div className="searchbar">
        <input
          className="search-input"
          type="search"
          placeholder="Search your recollections..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={
            (e) => {
              if (e.key === 'Enter') {
                searchAndPrompt(searchQuery);
              }
            }
          }
        />

        <button
          className="btn primary"
          onClick={
            () => {
              searchAndPrompt(searchQuery);
            }
          }
        >
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
