import React, { useState } from "react";
import type { DocumentMetadata } from "../api/api";

interface DocumentHeaderProps {
  document: DocumentMetadata;
  onRename?: (newName: string) => void;
  isEditable?: boolean;
}

const DocumentHeader: React.FC<DocumentHeaderProps> = ({
  document,
  onRename,
  isEditable = false
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(document.displayName);

  const handleEdit = () => {
    if (!isEditable) return;
    setIsEditing(true);
    setEditValue(document.displayName);
  };

  const handleSave = () => {
    if (editValue.trim() && editValue !== document.displayName && onRename) {
      onRename(editValue.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(document.displayName);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  return (
    <div className="flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mb-6">
      <div className="flex items-center space-x-3">
        {/* Document Icon */}
        <div className="flex-shrink-0 w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
          <svg
            className="w-6 h-6 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>

        {/* Document Name */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 px-3 py-1 text-lg font-semibold text-gray-900 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
                maxLength={100}
              />
              <button
                onClick={handleSave}
                className="px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Save
              </button>
              <button
                onClick={handleCancel}
                className="px-3 py-1 text-sm font-medium text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-semibold text-gray-900 truncate">
                {document.displayName}
              </h1>
              {isEditable && (
                <button
                  onClick={handleEdit}
                  className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 rounded-md hover:bg-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  title="Rename document"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
              )}
            </div>
          )}

          {/* Document ID (for reference) */}
          <p className="text-sm text-gray-500 mt-1">
            Document ID: {document.id.slice(0, 8)}...
          </p>
        </div>
      </div>

      {/* Status Indicator */}
      <div className="flex-shrink-0">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span className="text-sm font-medium text-green-700">Ready</span>
        </div>
      </div>
    </div>
  );
};

export default DocumentHeader;
