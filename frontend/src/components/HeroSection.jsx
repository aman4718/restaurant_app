export default function HeroSection() {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 mt-4">
      {/* Container with rounded corners and split background */}
      <div className="relative w-full h-[400px] rounded-3xl overflow-hidden flex shadow-sm">
        
        {/* Left side (Light Brand Color) */}
        <div className="w-1/2 h-full bg-brand-light relative z-10 flex flex-col justify-center pl-16 pr-8">
            <h2 className="text-[3.5rem] leading-[1.05] font-extrabold text-text-dark tracking-tight">
                Discover your next <br/>
                <span className="text-brand">culinary obsession.</span>
            </h2>
        </div>

        {/* Right side (Image Background) */}
        <div className="w-1/2 h-full relative">
            <div 
                className="absolute inset-0 bg-cover bg-center"
                style={{ 
                    backgroundImage: "url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&q=80&w=2070')",
                }}
            />
            {/* Gradient overlay to blend left to right smoothly */}
            <div className="absolute inset-0 bg-gradient-to-r from-brand-light via-brand-light/50 to-transparent" />
        </div>
      </div>
    </div>
  );
}
