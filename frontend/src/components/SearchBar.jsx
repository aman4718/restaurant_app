"use client";

import { useState, useEffect } from "react";
import { Search, MapPin, Utensils, IndianRupee } from "lucide-react";

export default function SearchBar({ onSearch, isLoading }) {
  const [locations, setLocations] = useState([]);
  const [cuisines, setCuisines] = useState([]);

  const [location, setLocation] = useState("Btm");
  const [cuisine, setCuisine] = useState("North Indian");
  const [budget, setBudget] = useState("medium");
  const [rating, setRating] = useState(4.0);

  useEffect(() => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${API_URL}/api/v1/options`)
      .then(res => res.json())
      .then(data => {
        setLocations(data.locations || []);
        setCuisines(data.cuisines || []);
      })
      .catch(err => console.error("Could not fetch options", err));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch({
      location,
      cuisine,
      min_rating: rating,
      budget,
    });
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 -mt-16 relative z-10">
      <form
        onSubmit={handleSubmit}
        className="bg-white md:rounded-[2.5rem] rounded-3xl shadow-xl shadow-brand/5 p-2 md:p-4 flex flex-col md:flex-row items-stretch md:items-center gap-0 md:gap-4 justify-between"
      >
        {/* Location Dropdown (Searchable) */}
        <div className="flex-1 w-full px-4 py-3 border-b md:border-b-0 md:border-r border-gray-100">
          <label className="text-[10px] font-bold text-gray-400 tracking-wider uppercase mb-1 flex items-center gap-1">
            <MapPin className="w-3 h-3" /> Location
          </label>
          <input
            list="location-options"
            className="w-full font-semibold text-text-dark bg-transparent outline-none focus:text-brand cursor-text truncate"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Type or select..."
          />
          <datalist id="location-options">
            {locations.map((loc) => (
              <option key={loc} value={loc} />
            ))}
          </datalist>
        </div>

        {/* Cuisine (Searchable) */}
        <div className="flex-1 w-full px-4 py-3 border-b md:border-b-0 md:border-r border-gray-100">
          <label className="text-[10px] font-bold text-gray-400 tracking-wider uppercase mb-1 flex items-center gap-1">
            <Utensils className="w-3 h-3" /> Cuisine
          </label>
          <input
            list="cuisine-options"
            className="w-full font-semibold text-text-dark bg-transparent outline-none focus:text-brand cursor-text truncate"
            value={cuisine}
            onChange={(e) => setCuisine(e.target.value)}
            placeholder="Type or select..."
          />
          <datalist id="cuisine-options">
            {cuisines.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </div>

        {/* Budget */}
        <div className="flex-1 w-full px-4 py-3 border-b md:border-b-0 md:border-r border-gray-100">
          <label className="text-[10px] font-bold text-gray-400 tracking-wider uppercase mb-1 flex items-center gap-1">
            <IndianRupee className="w-3 h-3" /> Budget
          </label>
          <select
            className="w-full font-semibold text-text-dark bg-transparent outline-none focus:text-brand cursor-pointer appearance-none"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          >
            <option value="low">Low (&lt; ₹500)</option>
            <option value="medium">Medium (₹500-1500)</option>
            <option value="high">High (&gt; ₹1500)</option>
          </select>
        </div>

        {/* Rating Slider (inline row below basically, but keeping in flex for simplicity, or we do it inline here) */}
        <div className="flex-[0.8] w-full px-4 py-3">
            <div className="flex justify-between items-center mb-1">
                <label className="text-[10px] font-bold text-gray-400 tracking-wider uppercase">
                Min. Rating:
                </label>
                <span className="text-brand font-bold text-xs">{rating.toFixed(1)}+</span>
            </div>
            
            <input 
                type="range" 
                min="0" max="5" step="0.1" 
                value={rating} 
                onChange={e => setRating(parseFloat(e.target.value))}
                className="w-full h-1 bg-brand-light rounded-lg appearance-none cursor-pointer accent-brand"
            />
        </div>

        {/* Find Button */}
        <div className="px-4 md:pl-4 md:pr-1 pt-2 md:pt-0">
          <button
            type="submit"
            disabled={isLoading}
            className="bg-brand hover:bg-brand-hover text-white font-bold py-4 px-8 rounded-full transition-all shadow-lg hover:shadow-brand/30 disabled:opacity-50 whitespace-nowrap"
          >
            {isLoading ? "Curating..." : "Get Restaurant"}
          </button>
        </div>
      </form>
    </div>
  );
}
