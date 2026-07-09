const AppShell = ({
  sidebar,
  header,
  banner,
  mobileNavigation,
  children,
}) => (
  <div className="app-shell dashboard-screen">
    {sidebar}

    <main className="app-shell__main">
      <div className="app-shell__content">
        {header && (
          <header className="app-shell__header">
            {header}
          </header>
        )}

        {banner}

        <div className="app-shell__page">
          {children}
        </div>
      </div>
    </main>

    {mobileNavigation}
  </div>
);

export default AppShell;
