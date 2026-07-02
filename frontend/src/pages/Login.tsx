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
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={getRoleHome(user.role)} replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!srn.trim() || !password.trim()) {
      setError("Please enter both SRN and password.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const role = await login(srn, password);
      navigate(getRoleHome(role));
    } catch {
      setError("Login failed. Check your credentials and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="gradient-cta dot-pattern hidden items-center p-12 text-white lg:flex">
        <div className="max-w-lg">
          <Logos invert className="mb-10" />
          <h1 className="text-4xl font-bold">Agentic AI Entrepreneurship Platform</h1>
          <p className="mt-5 text-white/78">A guided AI workspace for PES students and CIE mentors to validate ideas with disciplined evidence.</p>
        </div>
      </section>
      <section className="flex items-center justify-center p-5">
        <form onSubmit={onSubmit} className="w-full max-w-md rounded-lg border bg-white p-6 shadow-lg">
          <Logos className="mb-8 justify-center lg:hidden" />
          <h2 className="text-2xl font-bold text-primary">Sign in</h2>
          <p className="mt-2 text-sm text-muted-foreground">Sign in with your PES credentials. Your role is assigned at login.</p>
          <label className="mt-6 block text-sm font-semibold">SRN</label>
          <Input className="mt-2" value={srn} onChange={(e) => setSrn(e.target.value)} placeholder="PES2UG22CS001" />
          <label className="mt-4 block text-sm font-semibold">Password</label>
          <Input className="mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" />
          {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>}
          <Button disabled={loading} variant="secondary" className="mt-6 w-full">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign In
          </Button>
          <p className="mt-6 text-center text-xs text-muted-foreground">By continuing, you agree to PES CIE platform terms and privacy notice.</p>
        </form>
      </section>
    </main>
  );
}
