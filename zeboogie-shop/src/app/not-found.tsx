import Link from "next/link";

export default function NotFound() {
  return (
    <section className="container-x py-28 text-center">
      <p className="eyebrow">Ошибка 404</p>
      <h1 className="mt-4 text-5xl md:text-7xl">Здесь ничего нет</h1>
      <p className="mx-auto mt-5 max-w-md text-ink-soft">Возможно, изделие уже нашло свой дом или адрес набран с ошибкой.</p>
      <Link href="/catalog" className="btn btn-solid mt-8">Смотреть каталог</Link>
    </section>
  );
}
