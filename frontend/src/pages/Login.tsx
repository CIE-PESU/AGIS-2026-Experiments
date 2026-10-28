import { FormEvent, useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Logos } from "@/components/shared/Logos";
import { getRoleHome } from "@/components/shared/RequireRole";
import { useAuth } from "@/context/AuthContext";

export function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get("redirect") || null;

  const [srn, setSrn] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    const destination = redirectTo || getRoleHome(user.role);
    return <Navigate to={destination} replace />;
  }

  const nonStudentRoles = ["admin", "ashwin", "bhavesh", "urav"];
  const isStudent = !nonStudentRoles.includes(srn.toLowerCase()) && !srn.includes("@");

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
      const destination = redirectTo || getRoleHome(role);
      navigate(destination);
    } catch {
      setError("Login failed. Check your credentials and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/40 dot-pattern p-5">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-lg border bg-background p-8 shadow-xl">
        <div className="flex justify-center mb-6">
          <Logos />
        </div>
        <h2 className="text-2xl font-bold text-center text-primary">Sign in</h2>
        <p className="mt-2 text-sm text-center text-muted-foreground">Sign in with your PES credentials. Your role is assigned at login.</p>

        <label htmlFor="login-srn" className="mt-6 block text-sm font-semibold text-foreground">SRN</label>
        <Input
          className="mt-2"
          value={srn}
          onChange={(e) => setSrn(e.target.value)}
          id="login-srn" autoComplete="username"
          placeholder="PES2UG22CS001"
        />

        <label htmlFor="login-password" className="mt-4 block text-sm font-semibold text-foreground">Password</label>
        <Input
          className="mt-2"
          id="login-password" autoComplete="current-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter password"
        />

        {error && <div className="mt-4 rounded-lg bg-destructive/10 p-3 text-sm font-semibold text-destructive">{error}</div>}

        <Button disabled={loading} variant="secondary" className="mt-6 w-full">
          {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          Sign In
        </Button>
        <p className="mt-6 text-center text-xs text-muted-foreground">By continuing, you agree to PES CIE platform terms and privacy notice.</p>
      </form>
    </main>
  );
}
