import { Heart, Star } from "lucide-react";

export default function RestaurantCard({ restaurant, isTopPick, searchedCuisine }) {
  // A collection of great, verified restaurant/food image IDs
  // Verified high-quality food image IDs from Unsplash
  const imageIds = [
    "1504674900247-0877df9cc836", // salad
    "1512621776951-a57141f2eefd", // gourmet
    "1555939594-58d7cb561ad1", // kebab
    "1567622646611-2033069c9b46", // dessert
    "1565299624946-b28f40a0ae38", // pizza
    "1473093226795-af9932fe5856", // pasta
    "1540189549336-e6e99c3679fe", // meal
    "1565958011703-44f9829ba187"  // sushi
  ];
  
  const seed = restaurant.name.length + (restaurant.cuisines ? restaurant.cuisines.length : 0);
  const imgSrc = `https://images.unsplash.com/photo-${imageIds[seed % imageIds.length]}?auto=format&fit=crop&q=80&w=600`;

  return (
    <div className="flex flex-col rounded-3xl overflow-hidden bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(194,26,48,0.1)] transition-all duration-300 transform hover:-translate-y-1">
      {/* Image Area */}
      <div className="relative h-60 w-full">
        <img 
          src={imgSrc} 
          alt={restaurant.name}
          className="absolute inset-0 w-full h-full object-cover"
          onError={(e) => {
            e.target.onerror = null; // Prevent infinite loop if fallback also fails
            e.target.src = "https://images.unsplash.com/photo-1512152272829-451f28bc95b2?auto=format&fit=crop&q=80&w=600";
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent pointer-events-none" />
        
        {/* Badges */}
        {isTopPick && (
          <div className="absolute top-4 left-4 bg-brand text-white text-[10px] font-extrabold uppercase px-3 py-1.5 rounded-full tracking-wider shadow-md">
            #1 Top Pick
          </div>
        )}
        
        <button className="absolute top-4 right-4 h-9 w-9 bg-black/40 backdrop-blur-md rounded-full flex items-center justify-center hover:bg-brand transition-colors text-white">
          <Heart className="w-5 h-5 pointer-events-none" />
        </button>
      </div>

      {/* Content Area */}
      <div className="p-6 flex-1 flex flex-col">
        <div className="flex justify-between items-start gap-4 mb-3">
            <h3 className="text-xl md:text-2xl font-bold text-text-dark leading-tight line-clamp-1">{restaurant.name}</h3>
            {restaurant.rating !== null && (
                <div className="flex items-center gap-1 bg-brand-light/50 px-2 py-1 rounded-md text-brand font-bold text-sm shrink-0">
                    <Star className="w-3.5 h-3.5 fill-current" />
                    {restaurant.rating.toFixed(1)}
                </div>
            )}
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
            {(() => {
                const cuisines = [...restaurant.cuisines];
                if (searchedCuisine) {
                    const index = cuisines.findIndex(c => c.toLowerCase() === searchedCuisine.toLowerCase());
                    if (index > -1) {
                        const [found] = cuisines.splice(index, 1);
                        cuisines.unshift(found);
                    }
                }
                return cuisines.slice(0, 3).map((cuisine, i) => (
                    <span key={i} className="text-[10px] font-bold text-brand uppercase bg-brand-light px-2.5 py-1 rounded-full tracking-wider">
                        {cuisine}
                    </span>
                ));
            })()}
        </div>

        <div className="flex items-center text-sm font-medium text-gray-500 mb-6 gap-2">
            {restaurant.cost_for_two !== null ? `₹${restaurant.cost_for_two} for two` : "Price N/A"}
            <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
            <span>Local area</span>
        </div>

        {/* AI Insight Box */}
        <div className="mt-auto bg-brand-light/40 rounded-xl p-4 border border-brand/5 relative overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-brand/30"></div>
            <p className="text-sm italic text-text-dark/80 font-medium leading-relaxed">
                &quot;{restaurant.explanation}&quot;
            </p>
        </div>
      </div>
    </div>
  );
}
