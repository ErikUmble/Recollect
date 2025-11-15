import React, { useState, useEffect } from 'react';

type Dir = { name: string; full: string };

type DirectoryBrowserProps = {
  open: boolean;
  currentPath: string;
  onClose: () => void;
  onSelect: (path: string) => void;
  apiBase: string;
  log: (msg: string, type?: 'info' | 'success' | 'error') => void;
};

const DirectoryBrowser: React.FC<DirectoryBrowserProps> = ({
  open,
  currentPath,
  onClose,
  onSelect,
  apiBase,
  log,
}) => {
  const [dirs, setDirs] = useState<Dir[]>([]);
  const [browserPath, setBrowserPath] = useState(currentPath || '.');

  const fetchDirs = async (path: string) => {
    try {
      const resp = await fetch(`${apiBase}/api/list-dirs?path=${encodeURIComponent(path)}`);
      const data = await resp.json();
      setDirs(data.dirs || []);
      setBrowserPath(path);
    } catch (e: any) {
      log(e.message, 'error');
    }
  };

  const goUp = () => {
    const parts = browserPath.split(/[/\\]/);
    if (parts.length > 1) {
      const parent = parts.slice(0, -1).join('/');
      fetchDirs(parent || '.');
    }
  };

  useEffect(() => {
    if (open) {
      fetchDirs(browserPath);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <span>Choose Directory</span>
          <button className="btn" onClick={onClose}>
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
              <button className="btn primary" onClick={() => onSelect(d.full)}>
                Select
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DirectoryBrowser;
