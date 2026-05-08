<template>
  <div class="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-primary/20">
    <!-- Navigation -->
    <nav class="fixed top-0 left-0 right-0 z-50 transition-all duration-300" :class="{ 'bg-background/80 backdrop-blur-md border-b border-border/30': isScrolled }">
      <div class="container mx-auto px-6 h-20 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <span class="text-white font-bold text-xl">T</span>
          </div>
          <span class="font-heading font-bold text-xl tracking-tight">TaxFluent</span>
        </div>

        <div class="hidden md:flex items-center gap-8">
          <a href="#features" class="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">Features</a>
          <a href="#how-it-works" class="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">How it Works</a>
          <a href="#pricing" class="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">Pricing</a>
        </div>

        <div class="flex items-center gap-4">
          <Button variant="ghost" class="hidden sm:flex" @click="$router.push('/login')">Sign In</Button>
          <Button variant="glow" @click="$router.push('/register')">Get Started</Button>
        </div>
      </div>
    </nav>

    <!-- Hero Section -->
    <section class="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
      <!-- Background Elements -->
      <div class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-7xl pointer-events-none">
        <div class="absolute top-20 left-10 w-72 h-72 bg-primary/20 rounded-full blur-[100px] animate-pulse-glow"></div>
        <div class="absolute bottom-20 right-10 w-96 h-96 bg-accent/20 rounded-full blur-[100px] animate-pulse-glow" style="animation-delay: 1s"></div>
      </div>

      <div class="container mx-auto px-6 relative z-10">
        <div class="flex flex-col lg:flex-row items-center gap-12 lg:gap-20">
          <div class="flex-1 text-center lg:text-left">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 mb-6">
              <span class="w-2 h-2 rounded-full bg-accent animate-pulse"></span>
              <span class="text-xs font-medium text-primary">AI-Powered Tax Filing for AY 2025-26</span>
            </div>

            <h1 class="text-5xl lg:text-7xl font-heading font-bold leading-[1.1] mb-6">
              Tax Filing, <br />
              <span class="text-gradient">Reimagined.</span>
            </h1>

            <p class="text-lg text-muted-foreground mb-8 max-w-xl mx-auto lg:mx-0 leading-relaxed">
              Experience Financial Zen. Our multi-agent AI handles the complexity of Indian tax laws while you watch your finances flow in real-time.
            </p>

            <div class="flex flex-col sm:flex-row items-center gap-4 justify-center lg:justify-start">
              <Button size="lg" variant="glow" class="w-full sm:w-auto h-12 px-8 text-base" @click="$router.push('/register')">
                Start Filing Free
              </Button>
              <Button size="lg" variant="outline" class="w-full sm:w-auto h-12 px-8 text-base backdrop-blur-sm">
                Watch Demo
              </Button>
            </div>

            <div class="mt-10 flex items-center justify-center lg:justify-start gap-6 text-sm text-muted-foreground">
              <div class="flex items-center gap-2">
                <CheckCircle class="w-4 h-4 text-accent" />
                <span>ITR-1 & ITR-4</span>
              </div>
              <div class="flex items-center gap-2">
                <CheckCircle class="w-4 h-4 text-accent" />
                <span>Max Refund Guarantee</span>
              </div>
              <div class="flex items-center gap-2">
                <CheckCircle class="w-4 h-4 text-accent" />
                <span>Bank-Grade Security</span>
              </div>
            </div>
          </div>

          <div class="flex-1 w-full max-w-lg lg:max-w-none perspective-1000">
            <div class="relative transform rotate-y-12 rotate-x-6 transition-transform duration-500 hover:rotate-0">
              <Card class="glass-panel p-6 relative z-20 overflow-hidden">
                <!-- Mock UI -->
                <div class="flex items-center justify-between mb-6">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary">
                      <Bot class="w-6 h-6" />
                    </div>
                    <div>
                      <div class="font-medium">Tax Expert Agent</div>
                      <div class="text-xs text-muted-foreground">Analyzing deductions...</div>
                    </div>
                  </div>
                  <div class="px-2 py-1 rounded bg-green-500/10 text-green-600 dark:text-green-500 text-xs font-medium">Active</div>
                </div>

                <div class="space-y-4">
                  <div class="p-4 rounded-lg bg-muted/50 border border-border/40">
                    <div class="flex justify-between text-sm mb-2">
                      <span class="text-muted-foreground">Potential Refund</span>
                      <span class="font-bold text-green-600 dark:text-green-500">+ ₹24,500</span>
                    </div>
                    <div class="h-2 bg-muted rounded-full overflow-hidden">
                      <div class="h-full bg-green-500 w-[75%]"></div>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <div class="flex gap-3 items-start p-3 rounded-lg hover:bg-muted/50 transition-colors">
                      <div class="w-6 h-6 rounded bg-blue-500/10 flex items-center justify-center mt-0.5">
                        <FileText class="w-3 h-3 text-blue-500" />
                      </div>
                      <div class="text-sm">
                        <div class="font-medium">Form 16 Parsed</div>
                        <div class="text-xs text-muted-foreground">Gross Salary: ₹12,50,000</div>
                      </div>
                    </div>
                    <div class="flex gap-3 items-start p-3 rounded-lg hover:bg-muted/50 transition-colors">
                      <div class="w-6 h-6 rounded bg-purple-500/10 flex items-center justify-center mt-0.5">
                        <Sparkles class="w-3 h-3 text-purple-500" />
                      </div>
                      <div class="text-sm">
                        <div class="font-medium">Optimization Found</div>
                        <div class="text-xs text-muted-foreground">Switching to New Regime saves ₹12k</div>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              <!-- Floating Elements -->
              <Card class="absolute -right-10 top-20 p-4 glass-card w-48 animate-float z-30 hidden md:block">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                    <Check class="w-4 h-4 text-green-500" />
                  </div>
                  <div class="text-xs">
                    <div class="font-bold">Compliance Check</div>
                    <div class="text-muted-foreground">100% Verified</div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Grid -->
    <section id="features" class="py-20 bg-muted/30">
      <div class="container mx-auto px-6">
        <div class="text-center max-w-2xl mx-auto mb-16">
          <h2 class="text-3xl lg:text-4xl font-heading font-bold mb-4">Why Choose TaxFluent?</h2>
          <p class="text-muted-foreground">We combine the precision of code with the intuition of AI to deliver the most seamless filing experience ever.</p>
        </div>

        <div class="grid md:grid-cols-3 gap-8">
          <Card class="p-6 hover:-translate-y-2 transition-transform duration-300">
            <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6 text-primary">
              <BrainCircuit class="w-6 h-6" />
            </div>
            <h3 class="text-xl font-bold mb-3">Multi-Agent Intelligence</h3>
            <p class="text-muted-foreground text-sm leading-relaxed">
              Four specialized AI agents — Interviewer, Researcher, Calculator, Auditor — work in sequence to compute your ITR-1 with zero errors.
            </p>
          </Card>

          <Card class="p-6 hover:-translate-y-2 transition-transform duration-300">
            <div class="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mb-6 text-accent">
              <Activity class="w-6 h-6" />
            </div>
            <h3 class="text-xl font-bold mb-3">Glass-Box Tax Engine</h3>
            <p class="text-muted-foreground text-sm leading-relaxed">
              Every rupee explained. Click any tax line to see exactly why it was computed that way — slabs, rebates, cess, surcharge.
            </p>
          </Card>

          <Card class="p-6 hover:-translate-y-2 transition-transform duration-300">
            <div class="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center mb-6 text-purple-500">
              <ShieldCheck class="w-6 h-6" />
            </div>
            <h3 class="text-xl font-bold mb-3">Privacy First</h3>
            <p class="text-muted-foreground text-sm leading-relaxed">
              Your financial data is encrypted end-to-end. PAN and Aadhaar are stored with AES-256 encryption, never in plaintext.
            </p>
          </Card>
        </div>
      </div>
    </section>

    <!-- AI Features Showcase -->
    <section id="how-it-works" class="py-20">
      <div class="container mx-auto px-6">
        <div class="text-center max-w-2xl mx-auto mb-16">
          <h2 class="text-3xl lg:text-4xl font-heading font-bold mb-4">Powered by Adaptive AI</h2>
          <p class="text-muted-foreground">Not just a calculator — a system that learns how you work and explains every decision.</p>
        </div>

        <div class="grid md:grid-cols-2 gap-8">
          <!-- XAI -->
          <Card class="p-6 border border-primary/20 bg-primary/5">
            <div class="flex items-start gap-4 mb-4">
              <div class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0 text-blue-500">
                <FileText class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-lg font-bold mb-1">Explainable AI (XAI)</h3>
                <p class="text-sm text-muted-foreground">Every tax line item is explained in plain language. No black boxes.</p>
              </div>
            </div>
            <div class="rounded-lg bg-muted/40 border border-border/40 p-4 space-y-2 text-sm">
              <div class="flex justify-between items-center py-1 border-b border-border/30">
                <span class="text-muted-foreground">Gross Income</span>
                <span class="font-medium">₹12,50,000</span>
              </div>
              <div class="flex justify-between items-center py-1 border-b border-border/30">
                <span class="text-muted-foreground">Standard Deduction</span>
                <span class="font-medium text-green-600 dark:text-green-500">− ₹75,000</span>
              </div>
              <div class="flex justify-between items-center py-1 border-b border-border/30 cursor-pointer">
                <span class="text-primary font-medium">Rebate u/s 87A ▾</span>
                <span class="font-medium text-green-600 dark:text-green-500">− ₹25,000</span>
              </div>
              <div class="bg-blue-500/10 rounded p-2 text-xs text-blue-600 dark:text-blue-300">
                Since your taxable income is ≤ ₹7,00,000, you qualify for the full Section 87A rebate of ₹25,000.
              </div>
              <div class="flex justify-between items-center pt-1 font-semibold">
                <span>Tax Payable</span>
                <span class="text-primary">₹0</span>
              </div>
            </div>
          </Card>

          <!-- What-if / Regime Compare -->
          <Card class="p-6 border border-accent/20 bg-accent/5">
            <div class="flex items-start gap-4 mb-4">
              <div class="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center shrink-0 text-accent">
                <Sparkles class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-lg font-bold mb-1">What-If & Regime Comparison</h3>
                <p class="text-sm text-muted-foreground">Instantly see how 80C investments or regime switch changes your tax.</p>
              </div>
            </div>
            <div class="rounded-lg bg-muted/40 border border-border/40 p-4 space-y-3 text-sm">
              <div class="flex justify-between">
                <span class="text-muted-foreground">Old Regime Tax</span>
                <span class="font-medium">₹1,04,000</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">New Regime Tax</span>
                <span class="font-medium text-green-600 dark:text-green-500">₹78,000</span>
              </div>
              <div class="bg-green-500/10 rounded p-3 text-xs text-green-700 dark:text-green-400">
                <strong>New regime saves ₹26,000</strong> for your income level. Switch recommended.
              </div>
              <div class="pt-1 border-t border-border/30">
                <p class="text-xs text-muted-foreground">Invest ₹1,50,000 in 80C →</p>
                <p class="text-xs text-green-700 dark:text-green-400 font-medium mt-1">Saves additional ₹15,600 in old regime</p>
              </div>
            </div>
          </Card>

          <!-- Adaptive Mode -->
          <Card class="p-6 border border-purple-500/20 bg-purple-500/5">
            <div class="flex items-start gap-4 mb-4">
              <div class="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center shrink-0 text-purple-500">
                <BrainCircuit class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-lg font-bold mb-1">Adaptive Filing Interface</h3>
                <p class="text-sm text-muted-foreground">The UI learns from how you interact — suggests simpler or expert mode automatically.</p>
              </div>
            </div>
            <div class="rounded-lg bg-muted/40 border border-border/40 p-4 space-y-2 text-sm">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
                <span class="text-xs text-yellow-600 dark:text-yellow-400">Cognitive load detected</span>
              </div>
              <p class="text-xs text-muted-foreground">You've hit 3 field errors and clicked help twice. Would you like to switch to <strong class="text-foreground">Novice (Guided)</strong> mode?</p>
              <div class="flex gap-2 pt-1">
                <button class="px-3 py-1 text-xs bg-primary/20 text-primary rounded-full font-medium">Yes, switch</button>
                <button class="px-3 py-1 text-xs bg-muted rounded-full text-muted-foreground">Stay in expert</button>
              </div>
            </div>
          </Card>

          <!-- Senior Citizen Slabs -->
          <Card class="p-6 border border-orange-500/20 bg-orange-500/5">
            <div class="flex items-start gap-4 mb-4">
              <div class="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center shrink-0 text-orange-500">
                <ShieldCheck class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-lg font-bold mb-1">Senior Citizen Smart Slabs</h3>
                <p class="text-sm text-muted-foreground">Automatically applies higher exemptions for senior (60–79) and super-senior (80+) citizens.</p>
              </div>
            </div>
            <div class="rounded-lg bg-muted/40 border border-border/40 p-4 space-y-2 text-sm">
              <div class="flex justify-between py-1 border-b border-border/30">
                <span class="text-muted-foreground">General (under 60)</span>
                <span class="font-medium">₹2,50,000 exempt</span>
              </div>
              <div class="flex justify-between py-1 border-b border-border/30 text-orange-600 dark:text-orange-300">
                <span>Senior (60–79 yrs)</span>
                <span class="font-semibold">₹3,00,000 exempt</span>
              </div>
              <div class="flex justify-between py-1 text-orange-600 dark:text-orange-400">
                <span>Super Senior (80+)</span>
                <span class="font-semibold">₹5,00,000 exempt</span>
              </div>
              <p class="text-xs text-muted-foreground pt-1">Detected automatically from your age — no manual selection needed.</p>
            </div>
          </Card>
        </div>
      </div>
    </section>

    <!-- How it Works -->
    <section id="pricing" class="py-20 bg-muted/30">
      <div class="container mx-auto px-6">
        <div class="text-center max-w-2xl mx-auto mb-12">
          <h2 class="text-3xl lg:text-4xl font-heading font-bold mb-4">File in 3 Steps</h2>
          <p class="text-muted-foreground">From Form 16 upload to ITR-1 submission — guided by AI every step.</p>
        </div>
        <div class="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div class="text-center">
            <div class="w-14 h-14 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center mx-auto mb-4 text-primary font-bold text-xl">1</div>
            <h3 class="font-bold mb-2">Upload Form 16</h3>
            <p class="text-sm text-muted-foreground">OCR auto-reads your salary slip. TDS, employer, and income data pre-filled instantly.</p>
          </div>
          <div class="text-center">
            <div class="w-14 h-14 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center mx-auto mb-4 text-accent font-bold text-xl">2</div>
            <h3 class="font-bold mb-2">Chat with Tax AI</h3>
            <p class="text-sm text-muted-foreground">Our AI asks the right questions based on your profile — deductions, HRA, investments, and more.</p>
          </div>
          <div class="text-center">
            <div class="w-14 h-14 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center mx-auto mb-4 text-green-600 dark:text-green-500 font-bold text-xl">3</div>
            <h3 class="font-bold mb-2">Review & Submit</h3>
            <p class="text-sm text-muted-foreground">See a full explanation of your tax computation. Compare old vs new regime. Submit when ready.</p>
          </div>
        </div>
        <div class="text-center mt-10">
          <button @click="$router.push('/register')" class="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors">
            Start for free — no credit card needed
          </button>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-12 border-t border-border/30 bg-background">
      <div class="container mx-auto px-6">
        <div class="flex flex-col md:flex-row justify-between items-center gap-6">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">T</div>
            <span class="font-heading font-bold">TaxFluent</span>
          </div>
          <div class="text-sm text-muted-foreground">
            © 2025 TaxFluent AI. All rights reserved.
          </div>
          <div class="flex gap-6">
            <a href="#" class="text-muted-foreground hover:text-primary transition-colors"><Twitter class="w-5 h-5" /></a>
            <a href="#" class="text-muted-foreground hover:text-primary transition-colors"><Github class="w-5 h-5" /></a>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import Button from '@/components-vue/ui/Button.vue';
import Card from '@/components-vue/ui/Card.vue';
import {
  CheckCircle,
  Bot,
  FileText,
  Sparkles,
  Check,
  BrainCircuit,
  Activity,
  ShieldCheck,
  Twitter,
  Github
} from 'lucide-vue-next';

const isScrolled = ref(false);

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20;
};

onMounted(() => {
  window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<style scoped>
.perspective-1000 {
  perspective: 1000px;
}
.rotate-y-12 {
  transform: rotateY(-12deg) rotateX(5deg);
}
</style>
