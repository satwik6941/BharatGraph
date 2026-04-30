import { Navbar } from "@/components/Navbar";
import { Hero } from "@/components/Hero";
import { DemoSection } from "@/components/DemoSection";
import { Pipeline } from "@/components/Pipeline";
import { Features } from "@/components/Features";
import { Footer } from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <DemoSection />
        <Pipeline />
        <Features />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
