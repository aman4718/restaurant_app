import { Search, Sparkles, UserCircle2, Menu } from "lucide-react";

export default function Header() {
  return (
    <header className="w-full flex items-center justify-between py-6 px-8 max-w-7xl mx-auto">
      {/* Brand Logo */}
      <div className="flex items-center gap-2">
        <h1 className="text-brand font-extrabold text-2xl tracking-tight leading-none">
          Culinary<br/>Curator
        </h1>
      </div>

      {/* Nav Links */}
      <nav className="hidden md:flex items-center gap-8 font-semibold text-sm text-text-dark/80">
        <a href="#" className="text-brand hover:text-brand-hover">Home</a>
        <a href="#" className="hover:text-brand transition-colors">Explore</a>
        <a href="#" className="hover:text-brand transition-colors">About</a>
      </nav>

      {/* Actions */}
      <div className="flex items-center gap-5 text-brand">
        <button className="hover:opacity-80 transition-opacity">
          <Sparkles className="w-6 h-6" />
        </button>
        <button className="hover:opacity-80 transition-opacity">
          <UserCircle2 className="w-7 h-7" />
        </button>
        <button className="md:hidden">
          <Menu className="w-6 h-6" />
        </button>
      </div>
    </header>
  );
}
