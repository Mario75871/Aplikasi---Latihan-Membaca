import Link from "next/link";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { EmptyState } from "@/components/ui/States";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";

/** Halaman 404 — ramah dan selalu memberi jalan kembali. */
export default function NotFound() {
  return (
    <TeacherShell title="Halaman tidak ditemukan" breadcrumb="Dashboard">
      <EmptyState
        icon="inbox"
        title="Halaman ini tidak ditemukan"
        description="Mungkin tautannya sudah berubah atau datanya tidak tersedia."
        action={
          <Link href="/dashboard">
            <Button variant="primary" size="md">
              <Icon name="arrow-left" size={18} />
              Kembali ke Dashboard
            </Button>
          </Link>
        }
      />
    </TeacherShell>
  );
}
