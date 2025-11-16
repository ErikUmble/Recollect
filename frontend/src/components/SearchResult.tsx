import React, { useState } from 'react';
import '../App.css';

export type Result = {
  dir: string;
  matching_indices: number[];
  all_files: string[];
};

type SearchResultProps = {
  result: Result;
};
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000';

export const SearchResult: React.FC<SearchResultProps> = ({ result }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(result.matching_indices[0] || 0);

  const openModalAt = (i: number) => {
    setSelectedIndex(i);
    setModalOpen(true);
  };

  const closeModal = () => setModalOpen(false);

  const goLeft = () => {
    setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
  };

  const goRight = () => {
    setSelectedIndex((prev) => (prev < result.all_files.length - 1 ? prev + 1 : prev));
  };

  const currentFile = result.all_files[selectedIndex];

  return (
    <>
      <div className="result-block">
        {/* Directory name */}
        <div className="result-title">
          {result.dir.split('/').pop()}
        </div>

        {/* Thumbnails */}
        <div className="thumb-grid">
          {result.matching_indices.map((idx) => (
            <img
              key={idx}
              className="thumb"
              src={`${API_BASE}/api/file?path=${encodeURIComponent(result.all_files[idx])}`}
              onClick={() => openModalAt(idx)}
              alt={result.all_files[idx]}
            />
          ))}
        </div>
      </div>

      {/* Modal */}
      {modalOpen && (
        <div className="modal">
          <div className="modal-content">

            <div className="modal-header">
              <span>{currentFile}</span>
              <button className="btn" onClick={closeModal}>X</button>
            </div>

            <div className="modal-body">
              <button className="btn" onClick={goLeft} disabled={selectedIndex === 0}>
                ⬅
              </button>

              <img
                src={`${API_BASE}/api/file?path=${encodeURIComponent(currentFile)}`}
                alt={currentFile}
                style={{
                  maxWidth: '80%',
                  maxHeight: '60vh',
                  margin: '0 12px',
                  borderRadius: '6px'
                }}
              />

              <button
                className="btn"
                onClick={goRight}
                disabled={selectedIndex === result.all_files.length - 1}
              >
                ➡
              </button>
            </div>

            <div
              style={{
                marginTop: 6,
                fontSize: 11,
                color: 'var(--muted)',
                fontFamily: "'Inconsolata', monospace",
              }}
            >
              {selectedIndex + 1} / {result.all_files.length}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SearchResult;
