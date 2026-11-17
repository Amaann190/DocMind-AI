import React from "react";
import { LoaderCircle } from "lucide-react";
import { Brand } from "./components/ui.jsx";
import { ChatPage } from "./components/ChatPage.jsx";
import { LibraryPage } from "./components/LibraryPage.jsx";
import { SettingsPage } from "./components/SettingsPage.jsx";
import { Sidebar } from "./components/Sidebar.jsx";
import { ErrorBanner, TaskBanners } from "./components/StatusBanners.jsx";
import { Topbar } from "./components/Topbar.jsx";
import { WorkspaceModals } from "./components/WorkspaceModals.jsx";
import { WorkspaceProvider, useWorkspace } from "./state/WorkspaceContext.jsx";

function LoadingPage() {
  const { error, retry } = useWorkspace();
  return (
    <div className="loading-page">
      <Brand small />
      <h2>Opening your thinking space</h2>
      {error ? (
        <button className="primary" onClick={retry}>
          Try again
        </button>
      ) : (
        <LoaderCircle className="spin" />
      )}
    </div>
  );
}

function CurrentPage() {
  const { page, settings, disabled, saveSettings, setModal } = useWorkspace();
  if (page === "library") return <LibraryPage />;
  if (page === "settings")
    return (
      <SettingsPage settings={settings} disabled={disabled} save={saveSettings} reset={() => setModal("reset")} />
    );
  return <ChatPage />;
}

function Shell() {
  const { navigationVisible, panelWidths, workspace } = useWorkspace();
  return (
    <div
      className={"app-shell " + (!navigationVisible ? "navigation-hidden" : "")}
      style={{
        "--navigation-width": `${panelWidths.left}px`,
        "--sources-width": `${panelWidths.right}px`,
      }}
    >
      <Sidebar />
      <main className="main">
        <Topbar />
        <ErrorBanner />
        {!workspace ? (
          <LoadingPage />
        ) : (
          <>
            <TaskBanners />
            <CurrentPage />
          </>
        )}
      </main>
      <WorkspaceModals />
    </div>
  );
}

export function App() {
  return (
    <WorkspaceProvider>
      <Shell />
    </WorkspaceProvider>
  );
}
