import React, { useState } from 'react';
import '../App.css';

export type Result = {
  dir: string;
  match_index: number;
  all_files: string[]
};

type SearchResultProps = {
  result: Result;
};

export const SearchResult: React.FC<SearchResultProps> = ({ result }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(result.match_index);
  console.log(result);

  const openModal = () => {
    setCurrentIndex(result.match_index);
    setModalOpen(true);
  };

  const closeModal = () => setModalOpen(false);

  const goLeft = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : prev));
  };

  const goRight = () => {
    setCurrentIndex((prev) => (prev < result.all_files.length - 1 ? prev + 1 : prev));
  };

  return (
    <>
      {/* Search Result Item */}
      <div className="result" onClick={openModal} style={{ cursor: 'pointer' }}>
        { result.all_files[result.match_index].split('/').pop() }
      </div>

      {/* Modal for Image Viewer */}
      {modalOpen && (
        <div className="modal">
          <div className="modal-content">
            <div className="modal-header">
              <span>{result.all_files[currentIndex]}</span>
              <button className="btn" onClick={closeModal}>
                X
              </button>
            </div>
            <div className="modal-body">
              <button className="btn" onClick={goLeft} disabled={currentIndex === 0}>
                ⬅
              </button>
              <img
                src={`http://127.0.0.1:5000/api/file?path=${encodeURIComponent(
                  result.all_files[currentIndex]
                )}`}
                alt={result.all_files[currentIndex]}
                style={{ maxWidth: '80%', maxHeight: '60vh', margin: '0 12px', borderRadius: '6px' }}
              />
              <button className="btn" onClick={goRight} disabled={currentIndex === result.all_files.length - 1}>
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
              {currentIndex + 1} / {result.all_files.length}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SearchResult;
