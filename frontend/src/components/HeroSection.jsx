export default function HeroSection() {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 mt-4">
      {/* Container with rounded corners and split background */}
      <div className="relative w-full min-h-[400px] md:h-[400px] rounded-3xl overflow-hidden flex flex-col md:flex-row shadow-sm">
        
        {/* Left side (Light Brand Color) */}
        <div className="w-full md:w-1/2 h-full bg-brand-light relative z-10 flex flex-col justify-center px-6 py-12 md:pl-16 md:pr-8">
            <h2 className="text-4xl md:text-[3.5rem] leading-[1.1] md:leading-[1.05] font-extrabold text-text-dark tracking-tight">
                Discover your next <br/>
                <span className="text-brand">culinary obsession.</span>
            </h2>
            <p className="mt-4 text-text-dark/60 font-medium md:hidden">
                AI-powered restaurant recommendations tailored to your taste.
            </p>
        </div>

        {/* Right side (Image Background) */}
        <div className="w-full md:w-1/2 h-64 md:h-full relative">
            <div 
                className="absolute inset-0 bg-cover bg-center"
                style={{ 
                    backgroundImage: "url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&q=80&w=2070')",
                }}
            />
            {/* Gradient overlay to blend left to right smoothly */}
            <div className="absolute inset-0 bg-gradient-to-b md:bg-gradient-to-r from-brand-light via-brand-light/50 md:via-brand-light/50 to-transparent" />
        </div>
      </div>
    </div>
  );
}
