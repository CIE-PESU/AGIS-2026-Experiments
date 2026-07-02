import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { LogOut, MessageSquare, Send, X } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Logos } from "@/components/shared/Logos";
import { getRoleHome } from "@/components/shared/RequireRole";
import { useAuth } from "@/context/AuthContext";
import { getComments, addComment, Comment } from "@/utils/adminData";

const names: Record<string, string> = {
  "/workspace": "Workspace",
  "/workspace/tipsc": "TIPS Evaluation",
  "/workspace/dfv": "DFV Analysis",
  "/workspace/discovery": "Customer Discovery"
};

export function WorkspaceLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatComments, setChatComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");

  const loadComments = useCallback(() => {
    if (user) {
      setChatComments(getComments(user.srn));
    }
  }, [user]);

  useEffect(() => {
    if (isChatOpen) {
      loadComments();
      const interval = setInterval(loadComments, 3000);
      return () => clearInterval(interval);
    }
  }, [isChatOpen, loadComments]);

  const handleSendComment = () => {
    if (!newComment.trim() || !user) return;
    const comment: Comment = {
      sender: `Student (${user.name})`,
      message: newComment.trim(),
      timestamp: new Date().toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })
    };
    addComment(user.srn, comment);
    setNewComment("");
    loadComments();
    toast.success("Message sent");
  };

  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "student") return <Navigate to={getRoleHome(user.role)} replace />;

  return (
    <div className="min-h-screen bg-muted/50 relative overflow-x-hidden">
      <header className="sticky top-0 z-30 border-b bg-white">
        <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-6">
            <Logos to="/workspace" />
            <p className="hidden text-sm font-semibold text-muted-foreground md:block">
              <Link to="/workspace" className="text-primary">Workspace</Link> &gt; {names[location.pathname] || "Current Page"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right text-xs sm:block">
              <p className="font-semibold">{user.name}</p>
              <p className="text-muted-foreground">{user.srn}{user.teamId ? ` · ${user.teamId}` : ""}</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary font-bold text-white">
              {user.name.charAt(0)}
            </div>
            
            {/* Toggle Messaging Window */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => setIsChatOpen(prev => !prev)}
              title="Messaging & Feedback"
              className={`h-9 w-9 relative border-primary/20 hover:bg-primary/5 ${isChatOpen ? "bg-primary/5 border-primary text-primary" : "text-slate-600"}`}
            >
              <MessageSquare className="h-4 w-4" />
            </Button>

            <Button variant="ghost" size="icon" onClick={() => void logout()} title="Logout">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>
      
      <Outlet />

      {/* Slide-over chat panel */}
      {isChatOpen && (
        <div className="fixed inset-y-0 right-0 z-50 w-80 md:w-96 bg-white shadow-2xl border-l flex flex-col transition-all duration-300 animate-in slide-in-from-right">
          {/* Header */}
          <div className="p-4 border-b flex justify-between items-center bg-slate-50">
            <div>
              <h3 className="font-bold text-primary text-sm">Feedback & Remarks</h3>
              <p className="text-xs text-muted-foreground">Collaborate with your CIE Mentor</p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setIsChatOpen(false)} className="h-8 w-8">
              <X className="h-4 w-4" />
            </Button>
          </div>
          
          {/* Messages list */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50">
            {chatComments.length === 0 ? (
              <div className="text-center py-10">
                <div className="inline-flex p-3 rounded-full bg-slate-100 text-slate-400 mb-2">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <p className="text-xs font-semibold text-slate-700">No remarks yet</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Your mentor's comments and replies will show up here.</p>
              </div>
            ) : (
              chatComments.map((c, i) => {
                const isMe = c.sender.toLowerCase().includes("student") || c.sender.includes(user.name);
                return (
                  <div key={i} className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}>
                    <span className="text-[9px] text-muted-foreground mb-0.5">{c.sender} • {c.timestamp}</span>
                    <div className={`p-3 rounded-lg max-w-[85%] text-xs leading-relaxed ${isMe ? "bg-primary text-white" : "bg-slate-200 text-slate-800"}`}>
                      {c.message}
                    </div>
                  </div>
                );
              })
            )}
          </div>
          
          {/* Input form */}
          <div className="p-3 border-t bg-white flex gap-2">
            <Input 
              value={newComment} 
              onChange={e => setNewComment(e.target.value)} 
              placeholder="Type your reply..." 
              onKeyDown={e => { if (e.key === "Enter") handleSendComment(); }}
              className="text-xs h-9"
            />
            <Button variant="secondary" onClick={handleSendComment} className="h-9 text-xs px-3">
              <Send className="h-3 w-3 mr-1" /> Send
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
