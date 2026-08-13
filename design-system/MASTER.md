# Design System: SAR + MS Tarımsal Hasar Analizi
**Tema Türü:** Data-Dense Dashboard (Koyu Tema Varsayılanlı)
**Versiyon:** 1.0.0
**Durum:** Kilitli (Locked)

## 1. Tasarım Felsefesi ve Temel İlkeler
Bu platform öncelikli olarak analiz ve veri görselleştirme amaçlıdır. Kullanıcıların (analistler, kamu görevlileri vb.) uzun süre ekrana bakacağı göz önünde bulundurularak **Accessible & Ethical** ve **Data-Dense Dashboard** prensipleri benimsenmiştir:
- **Göz Yorgunluğunu Azaltma:** Tamamen siyah (`#000000`) yerine antrasit, koyu gri-mavi (`#09090b` veya `#020817`) tonlarında bir koyu tema.
- **Yüksek Kontrast (A11Y):** Metin ve arka planlar arasındaki kontrast oranı WCAG AA (en az 4.5:1) standartlarında olmalıdır.
- **Odaklanma (Focus States):** Klavye navigasyonu için tüm interaktif öğelerde net ve erişilebilir focus ring (örn. `ring-2 ring-offset-2 ring-primary`).
- **Hareket (Motion):** Framer Motion ile geçişler yumuşak tutulmalı ancak `prefers-reduced-motion: reduce` her zaman saygı görmeli (gereksiz dekoratif hareketlerden kaçınılmalı). Performans odaklı yaklaşım.

## 2. Renk Paleti (CSS Değişkenleri)
```css
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
}

:root {
  /* Koyu Tema Varsayılan (Dark Mode Default) */
  --background: #09090b;
  --foreground: #fafafa;
  --card: #09090b;
  --card-foreground: #fafafa;
  --popover: #09090b;
  --popover-foreground: #fafafa;
  --primary: #fafafa;
  --primary-foreground: #18181b;
  --secondary: #27272a;
  --secondary-foreground: #fafafa;
  --muted: #27272a;
  --muted-foreground: #a1a1aa;
  --accent: #27272a;
  --accent-foreground: #fafafa;
  --destructive: #7f1d1d;
  --destructive-foreground: #fafafa;
  --border: #27272a;
  --input: #27272a;
  --ring: #d4d4d8;
  --radius: 0.5rem;
}
```
*Not: İleride hasar haritası için veri yoğunluklu ekranlara özel (örn. NDMI için yeşil-kahve spektrumu) harita paletleri eklenecektir.*

## 3. Tipografi
- **Yazı Tipi:** Inter veya sistem varsayılanı `sans-serif` ailesi. Dashboard için monospace sayısal değerler (tabular-nums) kullanılmalıdır.
- Büyük tablolar için text boyutları `text-sm` veya `text-xs` aralığında tutularak dikey yoğunluk artırılacaktır.

## 4. Bileşen Mimarisi (21st.dev + shadcn/ui)
Yeni bir bileşen gerektiğinde:
1. Projede öncelikle `shadcn/ui` bileşenleri aranır.
2. Özel dashboard kartları, form yapıları veya veri tabloları için **21st.dev Magic MCP** ile eşleşen bir bileşen taranır. (Örn: `data-table`, `bento-grid`, `animated-tabs`).
3. Sıfırdan bileşen yazılacaksa, veri tablosu virtualizer (`@tanstack/react-virtual`) içermeli, animasyonlar CSS yerine `framer-motion` (ve `useReducedMotion` hook'u gözetilerek) ile yönetilmelidir.

## 5. Pre-Delivery Checklist
Geliştirilen her UI bileşeni veya ekran PR/Merge öncesi şu testlerden geçmelidir:
- [ ] **Kontrast Oranı:** Metinler WCAG AA standartlarına uygun mu?
- [ ] **Klavye Focus:** `Tab` ile gezinildiğinde tüm aksiyon butonları ve form alanları görünür şekilde odaklanıyor mu?
- [ ] **Reduced-Motion:** `window.matchMedia('(prefers-reduced-motion: reduce)')` açıkken veya ilgili Framer config'inde animasyonlar `duration: 0` veya `fade`'e dönüyor mu?
- [ ] **Cursor State:** Tıklanabilir (pointer), yükleniyor (wait), engelli (not-allowed) cursor durumları net bir şekilde belirtilmiş mi?
- [ ] **Performans (Virtualization):** Render edilen parsel sayısı veya log tablosu 100 satırı aştığında `@tanstack/react-virtual` aktifleşiyor mu?

## 6. Sayfa Bazlı Overrideler
İlerleyen aşamalarda `design-system/pages/` altında harita ekranı (tam ekran widget'lar) ve analiz formlarına özel şablon yönergeleri oluşturulacaktır.
