import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ChatWindow from "./components/ChatWindow";
import Login from "./pages/Login";
import Register from "./pages/Register";
import AdminDashboard from "./pages/AdminDashboard";
import { isAuthenticated, isAdmin } from "./services/authApi";
import AdminHistory from "./pages/AdminHistory";
import AdminChat from "./pages/AdminChat";
import ChatLayout from "./components/Chatlayout";


function PublicRoute({ children }) {
  if (!isAuthenticated()) return children;
  return <Navigate to={isAdmin() ? "/admin/dashboard" : "/"} replace />;
}

function ProtectedUserRoute({ children }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (isAdmin()) return <Navigate to="/admin/dashboard" replace />;
  return children;
}

function ProtectedAdminRoute({ children }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (!isAdmin()) return <Navigate to="/" replace />;
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          }
        />

        {/* Chatbot user */}
        <Route
          path="/"
          element={
            <ProtectedUserRoute>
              <ChatLayout />
            </ProtectedUserRoute>
          }
        />

        {/* Chatbot admin — même */}
        <Route
          path="/admin/chat"
          element={
            <ProtectedAdminRoute>
              <AdminChat />
            </ProtectedAdminRoute>
          }
        />

        {/* Dashboard admin */}
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedAdminRoute>
              <AdminDashboard />
            </ProtectedAdminRoute>
          }
        />

        <Route path="*" element={<Navigate to="/login" replace />} />

        <Route
          path="/admin/history"
          element={
            <ProtectedAdminRoute>
              <AdminHistory />
            </ProtectedAdminRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
