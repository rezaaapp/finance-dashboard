const EmptyState = ({
  title,
  description,
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondaryAction,
  icon: Icon,
  compact = false,
}) => (
  <div className={`panel rounded-lg shadow-lg ${compact ? "p-4 sm:p-5" : "p-6"}`}>
    <div className={`mx-auto flex max-w-2xl flex-col items-center text-center ${
      compact ? "py-5" : "py-10"
    }`}>
      {Icon && (
        <div className="icon-badge rounded-xl p-4">
          <Icon size={compact ? 22 : 28} />
        </div>
      )}

      <h2 className={`${compact ? "mt-3 text-lg" : "mt-5 text-2xl"} font-bold text-main`}>
        {title}
      </h2>

      {description && (
        <p className="mt-3 text-sm leading-7 text-muted sm:text-base">
          {description}
        </p>
      )}

      {(actionLabel || secondaryLabel) && (
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-center">
          {actionLabel && (
            <button
              type="button"
              onClick={onAction}
              className="primary-button inline-flex min-h-11 items-center justify-center rounded-lg px-5 py-2.5 font-semibold"
            >
              {actionLabel}
            </button>
          )}

          {secondaryLabel && (
            <button
              type="button"
              onClick={onSecondaryAction}
              className="secondary-button inline-flex min-h-11 items-center justify-center rounded-lg px-5 py-2.5 font-semibold"
            >
              {secondaryLabel}
            </button>
          )}
        </div>
      )}
    </div>
  </div>
);

export default EmptyState;
