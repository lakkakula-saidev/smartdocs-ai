import React from "react";
import { useFileUpload, ACCEPT_DEFAULT } from "../hooks/useFileUpload";
import { DropZone } from "./upload/DropZone";
import { FileInfo } from "./upload/FileInfo";
import { UploadStatus } from "./upload/UploadStatus";

/**
 * UploadDocument
 *
 * Refactored to compose smaller, focused building blocks:
 * - useFileUpload(): encapsulates state & upload logic
 * - DropZone: purely presentational drag/drop + picker UI
 * - FileInfo: shows selected file, size, progress & clear action
 * - UploadStatus: renders error / success states with accessible roles
 *
 * Backwards compatible: keeps same props & behavior.
 */
interface Props {
  onUploaded: (docId: string) => void;
  onGoToChat?: (docId: string) => void;
  accept?: string;
  maxSizeMB?: number;
}

export function UploadDocument({
  onUploaded,
  onGoToChat,
  accept = ACCEPT_DEFAULT,
  maxSizeMB = 20
}: Props) {
  const {
    file,
    pending,
    successId,
    successDisplayName,
    error,
    dragActive,
    inputRef,
    progress,
    isUploading,
    isFinalizing,
    canUpload,
    openPicker,
    handleSelect,
    handleDrop,
    handleDrag,
    removeFile,
    reset,
    startUpload
  } = useFileUpload({ onUploaded, accept, maxSizeMB });

  const handleSubmit: React.FormEventHandler = (e) => {
    e.preventDefault();
    startUpload();
  };

  const statusLabel = pending?.progress === 1 ? "Uploaded" : undefined;

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="contents">
        <DropZone
          accept={accept}
          maxSizeMB={maxSizeMB}
          dragActive={dragActive}
          file={file}
          disabled={isUploading || isFinalizing}
          progress={progress}
          openPicker={openPicker}
          onSelect={handleSelect}
          onDrag={handleDrag}
          onDrop={handleDrop}
          inputRef={inputRef}
          ariaStatus={
            error
              ? `Upload error: ${error}`
              : successId
              ? `Upload successful. Document ID ${successId}`
              : file
              ? `File selected: ${file.name}`
              : undefined
          }
        >
          <FileInfo
            file={file}
            progress={progress}
            uploading={isUploading}
            complete={pending?.progress === 1}
            onClear={removeFile}
            statusLabel={statusLabel}
          />
        </DropZone>

        <UploadStatus
          error={error}
          successId={successId}
          onDismissError={reset}
          hideWhenEmpty
        />

        {/* Futuristic Button Panel */}
        <div className="mt-4 p-4 bg-gradient-to-r from-slate-900/50 to-slate-800/50 rounded-xl border border-slate-700/50 backdrop-blur-sm">
          {!successId ? (
            // Pre-upload state
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                type="submit"
                disabled={!canUpload}
                className="group relative flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:from-gray-600 disabled:to-gray-700 text-white font-medium rounded-lg transition-all duration-300 disabled:cursor-not-allowed overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="relative flex items-center justify-center gap-2">
                  {isUploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>
                        Uploading {Math.round((pending?.progress ?? 0) * 100)}%
                      </span>
                    </>
                  ) : isFinalizing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Finalizing...</span>
                    </>
                  ) : (
                    <>
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
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                        />
                      </svg>
                      <span>Upload Document</span>
                    </>
                  )}
                </div>
              </button>

              {file && !isUploading && !isFinalizing && (
                <button
                  type="button"
                  onClick={removeFile}
                  className="group px-4 py-3 bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white border border-slate-600/50 hover:border-slate-500/50 rounded-lg transition-all duration-300"
                >
                  <div className="flex items-center gap-2">
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                    <span>Remove</span>
                  </div>
                </button>
              )}
            </div>
          ) : (
            // Post-upload success state - Futuristic action panel
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-emerald-900/30 to-teal-900/30 rounded-lg border border-emerald-500/30">
                <div className="flex-shrink-0 w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center">
                  <svg
                    className="w-4 h-4 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-emerald-300">
                    {successDisplayName ||
                      `Document ${successId.slice(0, 8)}...`}
                  </div>
                  <div className="text-xs text-emerald-400/70">
                    Ready for analysis
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {onGoToChat && (
                  <button
                    type="button"
                    onClick={() => onGoToChat(successId)}
                    className="group relative px-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white font-medium rounded-lg transition-all duration-300 overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative flex items-center justify-center gap-2">
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
                          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                        />
                      </svg>
                      <span>Start Chat</span>
                    </div>
                  </button>
                )}

                <button
                  type="button"
                  onClick={reset}
                  className="group px-6 py-3 bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white border border-slate-600/50 hover:border-slate-500/50 rounded-lg transition-all duration-300"
                >
                  <div className="flex items-center justify-center gap-2">
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
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                    <span>Upload New</span>
                  </div>
                </button>
              </div>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}
