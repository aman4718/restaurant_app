"use client";

import { useState } from "react";
import Header from "@/components/Header";
import HeroSection from "@/components/HeroSection";
import SearchBar from "@/components/SearchBar";
import AiInsightsBanner from "@/components/AiInsightsBanner";
import RestaurantCard from "@/components/RestaurantCard";
import { SlidersHorizontal } from "lucide-react";

export default function Home() {
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [sortBy, setSortBy] = useState("rank");

  // Compute sorted results safely on the fly
  const sortedResults = [...results].sort((a, b) => {
    if (sortBy === "price_asc") return (a.cost_for_two || Infinity) - (b.cost_for_two || Infinity);
    if (sortBy === "price_desc") return (b.cost_for_two || 0) - (a.cost_for_two || 0);
    if (sortBy === "rating_desc") return (b.rating || 0) - (a.rating || 0);
    return a.rank - b.rank; // default rank
  });

  const handleSearch = async (preferences) => {
    setIsLoading(true);
    setHasSearched(true);
    setSummary("");
    setResults([]);

    try {
      // Connect to the FastAPI backend backend on port 8000
      const response = await fetch("http://localhost:8000/api/v1/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(preferences),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch recommendations");
      }

      const data = await response.json();
      setSummary(data.summary);
      setResults(data.items || []);
    } catch (error) {
      console.error("Search error:", error);
      setSummary("Our servers are taking a breather. Please ensure the Python backend is running on port 8000.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[var(--background)] pb-24">
      <Header />
      <HeroSection />
      <SearchBar onSearch={handleSearch} isLoading={isLoading} />
      <AiInsightsBanner summary={summary} />

      {/* Results Section */}
      <section className="max-w-7xl mx-auto px-4 mt-12">
        
        {/* Toolbar / Filters (Dynamic UI implementation) */}
        {(hasSearched || results.length > 0) && (
            <div className="flex items-center justify-between mb-8 opacity-0 animate-fade-in" style={{animationFillMode: 'forwards'}}>
                <div className="flex flex-wrap items-center gap-3">
                    <button 
                        onClick={() => setSortBy('rank')}
                        className={`font-bold text-sm px-5 py-2.5 rounded-full transition-colors ${sortBy === 'rank' ? 'bg-brand-light text-brand' : 'text-text-dark/70 hover:bg-gray-100'}`}
                    >
                        AI Recommended ({results.length})
                    </button>
                    <button 
                        onClick={() => setSortBy('rating_desc')}
                        className={`font-semibold text-sm px-5 py-2.5 rounded-full transition-colors ${sortBy === 'rating_desc' ? 'bg-brand text-white shadow-md' : 'text-text-dark/70 hover:bg-gray-100'}`}
                    >
                        Top Rated
                    </button>
                    <button 
                        onClick={() => setSortBy('price_asc')}
                        className={`font-semibold text-sm px-5 py-2.5 rounded-full transition-colors ${sortBy === 'price_asc' ? 'bg-brand text-white shadow-md' : 'text-text-dark/70 hover:bg-gray-100'}`}
                    >
                        Price: Low to High
                    </button>
                    <button 
                        onClick={() => setSortBy('price_desc')}
                        className={`font-semibold text-sm px-5 py-2.5 rounded-full transition-colors ${sortBy === 'price_desc' ? 'bg-brand text-white shadow-md' : 'text-text-dark/70 hover:bg-gray-100'}`}
                    >
                        Price: High to Low
                    </button>
                </div>
                <button className="flex items-center gap-2 text-text-dark font-semibold text-sm hover:text-brand transition-colors">
                    <SlidersHorizontal className="w-4 h-4" /> Filters
                </button>
            </div>
        )}

        {/* Loading State Spinner */}
        {isLoading && (
            <div className="w-full py-20 flex flex-col items-center justify-center gap-4">
                <div className="w-10 h-10 border-4 border-brand-light border-t-brand rounded-full animate-spin"></div>
                <p className="text-text-dark font-medium animate-pulse">Curating your recommendations using AI...</p>
            </div>
        )}

        {/* Grid */}
        {!isLoading && sortedResults.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {sortedResults.map((restaurant, idx) => (
              <RestaurantCard 
                key={`${restaurant.id}-${idx}`} 
                restaurant={restaurant} 
                isTopPick={idx === 0 && sortBy === 'rank'} 
              />
            ))}
          </div>
        )}
      </section>
      
      {/* Global simple animations via inline or globals.css not strictly needed but adding tailwind base animation util if supported */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fade-in { 0% { opacity: 0; transform: translateY(10px); } 100% { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fade-in 0.5s ease-out; }
      `}} />
    </main>
  );
}
