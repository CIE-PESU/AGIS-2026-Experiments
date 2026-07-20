import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StageResultCardProps {
  title: string;
  data: unknown;
}

export function StageResultCard({
  title,
  data,
}: StageResultCardProps) {
  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {Object.entries(data as Record<string, unknown>).map(([key, value]) => (
          <div key={key} className="border-b pb-2 last:border-b-0">
            <p className="font-semibold capitalize">
              {key.replaceAll("_", " ")}
            </p>

            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {typeof value === "object"
                ? JSON.stringify(value, null, 2)
                : String(value)}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}