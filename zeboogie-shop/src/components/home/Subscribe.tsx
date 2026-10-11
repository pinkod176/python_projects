import { ArrowUpRight } from "lucide-react";
import { brand } from "@/content/brand";
import { Reveal } from "@/components/ui/Reveal";

/** Подписка = сообщество ВКонтакте: рассылки на сайте нет, новые работы мастерская показывает там. */
export function Subscribe({ href }: { href?: string }) {
  if (!href) return null;
  const s = brand.subscribe;
  return (
    <section className="container-x pb-6" aria-labelledby="subscribe-h">
      <Reveal className="flex flex-col gap-6 rounded-lg border border-line bg-paper-2 p-6 md:flex-row md:items-center md:justify-between md:p-12">
        <div className="max-w-xl">
          <h2 id="subscribe-h" className="text-h3 font-light">{s.title}</h2>
          <p className="mt-3 text-ink-soft">{s.text}</p>
        </div>
        <a href={href} target="_blank" rel="noopener noreferrer" className="btn btn-solid shrink-0 self-start md:self-auto">
          {s.cta} <ArrowUpRight aria-hidden className="size-4" strokeWidth={1.75} />
        </a>
      </Reveal>
    </section>
  );
}
