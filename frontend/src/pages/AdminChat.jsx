import AdminSidebar from "../components/admin/AdminSidebar";
import ChatWindow   from "../components/ChatWindow";

function AdminChat() {
  return (
    <div className="min-h-screen flex">
      <AdminSidebar activePage="chat" />
      <div className="flex-1 flex flex-col min-w-0">
        <ChatWindow sessionId="admin_chat" />
      </div>
    </div>
  );
}

export default AdminChat;