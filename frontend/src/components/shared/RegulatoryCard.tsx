import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SessionDocument } from "@/types/api";

type Props = {
  data: SessionDocument["regulatory"] | null | undefined;
};

export function RegulatoryCard({ data }: Props) {
  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>✓ Regulatory Review</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">

        <Field
          label="Target Geography"
          value={data.target_geography}
        />

        <Field
          label="Industry Sector"
          value={data.industry_sector}
        />

        <div>
          <h4 className="font-semibold mb-3">
            Applicable Regulations
          </h4>

          <div className="space-y-4">
            {data.applicable_regulations.map((regulation, index) => (
              <div
                key={index}
                className="rounded-lg border p-4"
              >
                <div className="flex items-center justify-between">

                  <h5 className="font-semibold">
                    {regulation.name}
                  </h5>

                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      regulation.compliance_burden === "LOW"
                        ? "bg-green-100 text-green-700"
                        : regulation.compliance_burden === "MEDIUM"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {regulation.compliance_burden}
                  </span>
                </div>

                <p className="mt-2 text-sm font-medium">
                  Jurisdiction
                </p>

                <p className="text-muted-foreground">
                  {regulation.jurisdiction}
                </p>

                <p className="mt-3 text-sm font-medium">
                  Requirement
                </p>

                <p className="text-muted-foreground whitespace-pre-wrap">
                  {regulation.brief_requirement}
                </p>

              </div>
            ))}
          </div>
        </div>

        <Field
          label="Regulatory Summary"
          value={data.regulatory_summary}
        />

        <div className="rounded-lg border p-4">

          <h4 className="font-semibold mb-2">
            Specialist Review Required
          </h4>

          <span
            className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
              data.requires_specialist_review
                ? "bg-yellow-100 text-yellow-700"
                : "bg-green-100 text-green-700"
            }`}
          >
            {data.requires_specialist_review ? "YES" : "NO"}
          </span>

        </div>

        <div>

          <h4 className="font-semibold mb-3">
            Key Compliance Risks
          </h4>

          <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
            {data.key_compliance_risks.map((risk, index) => (
              <li key={index}>
                {risk}
              </li>
            ))}
          </ul>

        </div>

      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value?: string |null;
}) {
  return (
    <div className="border-b pb-3">
      <h4 className="font-semibold">
        {label}
      </h4>

      <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
        {value || "-"}
      </p>
    </div>
  );
}