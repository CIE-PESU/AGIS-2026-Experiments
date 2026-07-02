import { FormEvent, useState } from "react";
import { Loader2 } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Logos } from "@/components/shared/Logos";
import { getRoleHome } from "@/components/shared/RequireRole";
import { useAuth } from "@/context/AuthContext";

export function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [srn, setSrn] = useState("PES2UG22CS001");
  const [password, setPassword] = useState("");
  const [teamName, setTeamName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={getRoleHome(user.role)} replace />;

  const isStudent = srn.toLowerCase() !== "admin" && srn.toLowerCase() !== "mentor";

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!srn.trim() || !password.trim()) {
      setError("Please enter both SRN and password.");
      return;
    }
    if (isStudent && !teamName.trim()) {
      setError("Team Name is required for students.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const role = await login(srn, password, isStudent ? teamName : undefined);
      navigate(getRoleHome(role));
    } catch {
      setError("Login failed. Check your credentials and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/40 dot-pattern p-5">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-lg border bg-white p-8 shadow-xl">
        <div className="flex justify-center mb-6">
          <Logos />
        </div>
        <h2 className="text-2xl font-bold text-center text-primary">Sign in</h2>
        <p className="mt-2 text-sm text-center text-muted-foreground">Sign in with your PES credentials. Your role is assigned at login.</p>
        
        <label className="mt-6 block text-sm font-semibold text-slate-700">SRN</label>
        <Input 
          className="mt-2" 
          value={srn} 
          onChange={(e) => setSrn(e.target.value)} 
          placeholder="PES2UG22CS001" 
        />
        
        {isStudent && (
          <>
            <label className="mt-4 block text-sm font-semibold text-slate-700">Team Name</label>
            <Input 
              className="mt-2" 
              value={teamName} 
              onChange={(e) => setTeamName(e.target.value)} 
              placeholder="e.g. Team Gamma" 
            />
          </>
        )}
        
        <label className="mt-4 block text-sm font-semibold text-slate-700">Password</label>
        <Input 
          className="mt-2" 
          type="password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          placeholder="Enter password" 
        />
        
        {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>}
        
        <Button disabled={loading} variant="secondary" className="mt-6 w-full">
          {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          Sign In
        </Button>
        <p className="mt-6 text-center text-xs text-muted-foreground">By continuing, you agree to PES CIE platform terms and privacy notice.</p>
      </form>
    </main>
  );
}
