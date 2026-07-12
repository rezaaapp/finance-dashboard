import { BellRing, CheckCircle2, LoaderCircle, XCircle } from "lucide-react";
import { useState } from "react";

const WorkspaceInvitationNotification = ({
  invitations = [],
  actionInvitationId = "",
  error = "",
  onAccept,
  onDecline,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const invitationCount = invitations.length;

  if (invitationCount === 0) {
    return null;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
        className="theme-toggle relative h-11 min-w-11 rounded-lg px-3 py-2 font-semibold"
        aria-label={`${invitationCount} pending workspace invitation${invitationCount === 1 ? "" : "s"}`}
        title="Pending workspace invitations"
      >
        <BellRing size={18} />
        <span className="status-badge status-badge--danger absolute -right-1 -top-1 h-5 min-w-5 justify-center px-1 text-[11px]">
          {invitationCount}
        </span>
      </button>

      {isOpen && (
        <div className="dialog-panel absolute right-0 top-full z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] p-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-sm font-bold text-main">
              Pending Invitations
            </p>
            <span className="rounded-full bg-[var(--color-accent-bg)] px-2 py-1 text-xs font-bold text-accent">
              {invitationCount}
            </span>
          </div>

          {error && (
            <p className="alert-panel alert-panel--danger mb-2 px-3 py-2 text-xs font-semibold">
              {error}
            </p>
          )}

          <ul className="space-y-2">
            {invitations.map((invitation) => {
              const isActing = actionInvitationId === invitation.id;

              return (
                <li
                  key={invitation.id}
                  className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-main">
                      {invitation.workspace_name}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted">
                      Invited by {invitation.invited_by_name || "workspace owner"} as {invitation.role}
                    </p>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => onAccept(invitation.id)}
                      disabled={isActing}
                      className="primary-button min-h-9 rounded-lg px-3 py-1.5 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isActing ? (
                        <LoaderCircle size={14} className="animate-spin" />
                      ) : (
                        <CheckCircle2 size={14} />
                      )}
                      Accept
                    </button>

                    <button
                      type="button"
                      onClick={() => onDecline(invitation.id)}
                      disabled={isActing}
                      className="secondary-button min-h-9 rounded-lg px-3 py-1.5 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isActing ? (
                        <LoaderCircle size={14} className="animate-spin" />
                      ) : (
                        <XCircle size={14} />
                      )}
                      Decline
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

export default WorkspaceInvitationNotification;
