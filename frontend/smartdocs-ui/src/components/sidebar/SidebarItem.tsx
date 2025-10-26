import type { DocumentMetadata } from "../../api/api";

interface SidebarItemProps {
  document: DocumentMetadata & { created_at?: string };
  isActive?: boolean;
  onClick?: () => void;
}

export function SidebarItem({
  document,
  isActive = false,
  onClick
}: SidebarItemProps) {
  const handleClick = () => {
    onClick?.();
  };

  // Simple date formatting function
  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInDays > 0) {
      return `${diffInDays} day${diffInDays > 1 ? "s" : ""} ago`;
    } else if (diffInHours > 0) {
      return `${diffInHours} hour${diffInHours > 1 ? "s" : ""} ago`;
    } else {
      return "Just now";
    }
  };

  // Format creation date if available
  const createdDate = document.created_at
    ? formatTimeAgo(document.created_at)
    : null;

  return (
    <div
      onClick={handleClick}
      className={`
        group flex items-center p-3 rounded-lg cursor-pointer transition-all duration-200
        ${
          isActive
            ? "bg-brand-50 border border-brand-200 shadow-sm"
            : "hover:bg-gray-50 border border-transparent hover:border-gray-200"
        }
      `}
    >
      {/* Document title and date */}
      <div className="flex-1 min-w-0">
        <h3
          className={`
          text-sm font-medium truncate
          ${
            isActive
              ? "text-brand-700"
              : "text-gray-900 group-hover:text-gray-700"
          }
        `}
        >
          {document.displayName}
        </h3>

        {/* Creation date */}
        {createdDate && (
          <p className="text-xs text-gray-400 mt-0.5">{createdDate}</p>
        )}
      </div>

      {/* Status indicator */}
      {isActive && (
        <div className="w-2 h-2 bg-brand-500 rounded-full flex-shrink-0 ml-2"></div>
      )}
    </div>
  );
}
