import { brand } from "@/content/brand";

export function Values() {
  return (
    <section className="container-x py-16 md:py-24">
      <ul className="grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {brand.values.map((v, i) => (
          <li key={v.title} className="bg-paper p-6 md:p-8">
            <span aria-hidden className="font-serif text-sm text-wood">0{i + 1}</span>
            <h3 className="mt-6 font-serif text-xl">{v.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">{v.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
