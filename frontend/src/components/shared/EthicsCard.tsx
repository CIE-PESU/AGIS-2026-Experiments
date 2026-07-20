import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SessionDocument } from "@/types/api";

type Props = {
  data: SessionDocument["ethics"] | null | undefined;
};

export function EthicsCard({ data }: Props) {
  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>✓ Ethics Review</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">

        <TrafficField
          label="Harm Vector"
          status={data.harm_vector}
          description={data.harm_reason}
        />

        <TrafficField
          label="Legal Risk"
          status={data.legal_risk}
          description={data.legal_reason}
        />

        <TrafficField
          label="Problem–Solution Integrity"
          status={data.problem_solution_integrity}
          description={data.integrity_reason}
        />

        <div className="grid gap-4 md:grid-cols-2">

          <div className="rounded-lg border p-4">
            <h4 className="font-semibold mb-2">
              Ethics Decision
            </h4>

            <span
              className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                data.ethics_pass
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {data.ethics_pass ? "PASSED" : "FAILED"}
            </span>
          </div>

          <div className="rounded-lg border p-4">
            <h4 className="font-semibold mb-2">
              Compliance Flag
            </h4>

            <span
              className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                data.compliance_flag
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-green-100 text-green-700"
              }`}
            >
              {data.compliance_flag ? "YES" : "NO"}
            </span>
          </div>

        </div>

        {data.rejection_reason && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <h4 className="font-semibold text-red-700">
              Rejection Reason
            </h4>

            <p className="mt-2 text-red-600 whitespace-pre-wrap">
              {data.rejection_reason}
            </p>
          </div>
        )}

      </CardContent>
    </Card>
  );
}

function TrafficField({
  label,
  status,
  description,
}: {
  label: string;
  status: string;
  description: string;
}) {
  const styles = {
    GREEN: "bg-green-100 text-green-700",
    YELLOW: "bg-yellow-100 text-yellow-700",
    RED: "bg-red-100 text-red-700",
  };

  return (
    <div className="rounded-lg border p-4">

      <div className="flex items-center justify-between">

        <h4 className="font-semibold">
          {label}
        </h4>

        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            styles[status as keyof typeof styles]
          }`}
        >
          {status}
        </span>

      </div>

      <p className="mt-3 text-muted-foreground whitespace-pre-wrap">
        {description}
      </p>

    </div>
  );
}