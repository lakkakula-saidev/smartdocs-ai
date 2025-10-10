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
  accept?: string;
  maxSizeMB?: number;
}

export function UploadDocument({
  onUploaded,
  accept = ACCEPT_DEFAULT,
  maxSizeMB = 20
}: Props) {
  const {
    file,
    pending,
    successId,
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

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={!canUpload}
            className="btn disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isUploading
              ? `Uploading ${Math.round((pending?.progress ?? 0) * 100)}%`
              : isFinalizing
              ? "Finalizing..."
              : "Upload"}
          </button>

          {file && !isUploading && !isFinalizing && (
            <button
              type="button"
              onClick={removeFile}
              className="btn-outline disabled:opacity-40"
            >
              Remove
            </button>
          )}

          {successId && (
            <button
              type="button"
              onClick={reset}
              className="btn-outline text-[0.65rem]"
            >
              New Upload
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
