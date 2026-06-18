import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import GrantFinder from "./pages/GrantFinder";
import GrantTracker from "./pages/GrantTracker";
import ApplyHelper from "./pages/ApplyHelper";

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/find" element={<GrantFinder />} />
          <Route path="/tracker" element={<GrantTracker />} />
          <Route path="/apply/:grantId?" element={<ApplyHelper />} />
        </Routes>
      </main>
    </div>
  );
}
