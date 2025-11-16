import React, { useEffect, useState } from 'react';

type DirEntry = {
  name: string;
  full: string; // relative path from currentPath
};

type Props = {
  open: boolean;
  currentPath: string; // relative path selected so far
  onClose: () => void;
  onSelect: (path: string) => void; // called only when selecting final directory
  apiBase: string;
  log: (text: string, type?: 'info' | 'success' | 'error') => void;
};

const DirectoryBrowser: React.FC<Props> = ({ open, currentPath, onClose, onSelect, apiBase, log }) => {
  const [entries, setEntries] = useState<DirEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentViewPath, setCurrentViewPath] = useState(currentPath);

  // Update view path if currentPath prop changes
  useEffect(() => {
    setCurrentViewPath(currentPath);
  }, [currentPath]);

  // Fetch directories whenever currentViewPath changes
  useEffect(() => {
    if (!open) return;

    const fetchDirs = async () => {
      setLoading(true);
      try {
        const resp = await fetch(
          `${apiBase}/api/list-dirs?path=${encodeURIComponent(currentViewPath)}`
        );
        if (!resp.ok) throw new Error('Failed to list directories');
        const data = await resp.json();
        setEntries(data.dirs || []);
      } catch (e: any) {
        log(e.message, 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchDirs();
  }, [currentViewPath, apiBase, open]);

  if (!open) return null;

  const goUp = () => {
    if (currentViewPath === '.' || currentViewPath === '') return;
    const parent = currentViewPath.split('/').slice(0, -1).join('/') || '.';
    setCurrentViewPath(parent);
  };

  const enterDir = (name: string) => {
    const next = currentViewPath === '.' ? name : `${currentViewPath}/${name}`;
    setCurrentViewPath(next);
  };

  const handleSelect = () => {
    onSelect(currentViewPath); // final selection
    onClose(); // close modal
  };

  return (
    <div className="modal">
      <div className="modal-content" style={{ width: 400 }}>
        <div className="modal-header">
          <span>Choose Directory: {currentViewPath}</span>
          <button className="btn" onClick={onClose}>
            X
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '50vh', overflowY: 'auto' }}>
          <button className="btn" onClick={goUp} disabled={currentViewPath === '.'}>
            .. (Up)
          </button>

          {loading ? (
            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--muted)' }}>Loading...</div>
          ) : entries.length ? (
            <ul style={{ padding: 0, marginTop: 10, listStyle: 'none' }}>
              {entries.map((entry) => (
                <li key={entry.full} style={{ marginBottom: 6 }}>
                  <button
                    className="btn"
                    style={{ width: '100%', textAlign: 'left' }}
                    onClick={() => enterDir(entry.name)} // just navigate, don't select
                  >
                    {entry.name}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--muted)' }}>
              No subdirectories
            </div>
          )}
        </div>

        <div className="modal-footer" style={{ marginTop: 10 }}>
          <button className="btn primary" onClick={handleSelect}>
            Select This Directory
          </button>
        </div>
      </div>
    </div>
  );
};

export default DirectoryBrowser;
