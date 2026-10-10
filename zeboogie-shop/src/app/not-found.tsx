import Link from "next/link";

export default function NotFound() {
  return (
    <section className="container-x section-y text-center">
      <p className="eyebrow reveal-load">Ошибка 404</p>
      <h1 className="reveal-load mt-4 text-h1 font-light" style={{ "--reveal-delay": "80ms" } as React.CSSProperties}>Здесь ничего нет</h1>
      <p className="reveal-load mx-auto mt-6 max-w-md text-ink-soft" style={{ "--reveal-delay": "160ms" } as React.CSSProperties}>
        Возможно, изделие уже нашло свой дом или адрес набран с ошибкой.
      </p>
      <Link href="/catalog" className="btn btn-solid reveal-load mt-10" style={{ "--reveal-delay": "240ms" } as React.CSSProperties}>Смотреть каталог</Link>
    </section>
  );
}
