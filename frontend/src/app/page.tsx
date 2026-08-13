import { AoiMap } from "@/components/map/AoiMap";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">SAR + MS Analiz Platformu</h1>
          <p className="text-muted-foreground text-lg">
            Tarımsal hasar tespiti için Alan Seçimi (AOI) ve gerçek zamanlı izleme.
          </p>
        </header>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold tracking-tight">Çalışma Alanı (AOI) Seçimi</h2>
            {/* Buradashadcn ui ile bir buton eklenebilir */}
          </div>
          
          <AoiMap />
        </section>
      </div>
    </main>
  );
}
