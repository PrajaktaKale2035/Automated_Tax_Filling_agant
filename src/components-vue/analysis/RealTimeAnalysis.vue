<template>
  <div class="space-y-6">
    <!-- Live Status Bar -->
    <Card>
      <CardContent class="py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
            <span class="text-sm font-medium">Real-time Analysis Active</span>
          </div>
          <div class="text-xs text-muted-foreground">
            Last updated: {{ lastUpdate }}
          </div>
        </div>
      </CardContent>
    </Card>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Tax Optimization Metrics -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <TrendingUp class="h-5 w-5 text-primary" />
            Tax Optimization Metrics
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div v-for="metric in optimizationMetrics" :key="metric.label"
               class="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
            <div>
              <p class="text-sm font-medium">{{ metric.label }}</p>
              <p class="text-xs text-muted-foreground">{{ metric.description }}</p>
            </div>
            <div class="text-right">
              <p class="text-lg font-bold" :class="metric.value > 0 ? 'text-green-600' : 'text-primary'">
                {{ metric.value > 0 ? '+' : '' }}${{ formatNumber(metric.value) }}
              </p>
              <p class="text-xs text-muted-foreground">{{ metric.percentage }}%</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Compliance Score -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <Shield class="h-5 w-5 text-green-600" />
            Compliance Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
            <div class="relative pt-1">
              <div class="flex mb-2 items-center justify-between">
                <div>
                  <span class="text-3xl font-bold text-green-600">{{ complianceScore }}%</span>
                </div>
                <div class="text-right">
                  <span class="text-xs font-semibold inline-block text-green-600">
                    IRS Compliant
                  </span>
                </div>
              </div>
              <div class="overflow-hidden h-4 text-xs flex rounded-full bg-muted">
                <div :style="{ width: complianceScore + '%' }"
                     class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-gradient-to-r from-green-500 to-green-600 transition-all duration-500">
                </div>
              </div>
            </div>

            <div class="space-y-2 mt-4">
              <div v-for="check in complianceChecks" :key="check.label"
                   class="flex items-center justify-between text-sm">
                <span class="flex items-center gap-2">
                  <CheckCircle2 class="h-4 w-4 text-green-600" v-if="check.passed" />
                  <AlertCircle class="h-4 w-4 text-yellow-600" v-else />
                  {{ check.label }}
                </span>
                <span :class="check.passed ? 'text-green-600' : 'text-yellow-600'" class="text-xs font-medium">
                  {{ check.passed ? 'Passed' : 'Review' }}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Deduction Opportunities -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <Lightbulb class="h-5 w-5 text-yellow-600" />
            AI-Detected Opportunities
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-3">
            <div v-for="(opportunity, index) in opportunities" :key="index"
                 class="p-4 border rounded-lg hover:border-primary transition-colors cursor-pointer group">
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <h4 class="font-medium text-sm group-hover:text-primary transition-colors">
                    {{ opportunity.title }}
                  </h4>
                  <p class="text-xs text-muted-foreground mt-1">{{ opportunity.description }}</p>
                </div>
                <div class="ml-4 text-right">
                  <p class="text-sm font-bold text-green-600">+${{ formatNumber(opportunity.savings) }}</p>
                  <p class="text-xs text-muted-foreground">potential</p>
                </div>
              </div>
              <div class="mt-2 flex items-center gap-2">
                <span class="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                  {{ opportunity.category }}
                </span>
                <span class="text-xs text-muted-foreground">
                  Confidence: {{ opportunity.confidence }}%
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Tax Burden Timeline -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <BarChart3 class="h-5 w-5 text-primary" />
            Tax Burden Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
            <div v-for="bracket in taxBurdenByBracket" :key="bracket.rate"
                 class="space-y-2">
              <div class="flex items-center justify-between text-sm">
                <span class="font-medium">{{ bracket.rate }}% Bracket</span>
                <span class="text-muted-foreground">${{ formatNumber(bracket.amount) }}</span>
              </div>
              <div class="relative pt-1">
                <div class="overflow-hidden h-2 text-xs flex rounded-full bg-muted">
                  <div :style="{ width: bracket.percentage + '%', backgroundColor: bracket.color }"
                       class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center transition-all duration-500">
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- AI Insights -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
          <Sparkles class="h-5 w-5 text-purple-600" />
          AI-Powered Insights
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="insight in aiInsights" :key="insight.title"
               class="p-4 rounded-lg bg-gradient-to-br from-primary/5 to-primary/10 border border-primary/20">
            <component :is="insight.icon" class="h-6 w-6 text-primary mb-2" />
            <h4 class="font-semibold text-sm mb-1">{{ insight.title }}</h4>
            <p class="text-xs text-muted-foreground">{{ insight.description }}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import Card from '@/components-vue/ui/Card.vue';
import CardHeader from '@/components-vue/ui/CardHeader.vue';
import CardTitle from '@/components-vue/ui/CardTitle.vue';
import CardContent from '@/components-vue/ui/CardContent.vue';
import { 
  TrendingUp, Shield, Lightbulb, BarChart3, Sparkles, 
  CheckCircle2, AlertCircle, DollarSign, Target, Zap 
} from 'lucide-vue-next';

const lastUpdate = ref(new Date().toLocaleTimeString());
const complianceScore = ref(98);

const optimizationMetrics = ref([
  { label: 'Standard Deduction', description: '2024 IRS Standard', value: 14600, percentage: 19.5 },
  { label: 'Potential Savings', description: 'AI-identified opportunities', value: 2800, percentage: 3.7 },
  { label: 'Tax Credits', description: 'Eligible credits', value: 2000, percentage: 2.7 }
]);

const complianceChecks = ref([
  { label: 'Income Reporting (Form 1040)', passed: true },
  { label: 'Deduction Limits', passed: true },
  { label: 'Credit Eligibility', passed: true },
  { label: 'Filing Status Verification', passed: true },
  { label: 'Document Completeness', passed: false }
]);

const opportunities = ref([
  {
    title: 'Maximize Retirement Contributions',
    description: 'Contribute to IRA or 401(k) to reduce taxable income',
    savings: 1200,
    category: 'Retirement',
    confidence: 95
  },
  {
    title: 'Dependent Care FSA',
    description: 'Pre-tax account for child or elder care expenses',
    savings: 800,
    category: 'FSA',
    confidence: 88
  },
  {
    title: 'Health Savings Account',
    description: 'Triple tax advantage for medical expenses',
    savings: 600,
    category: 'Healthcare',
    confidence: 92
  }
]);

const taxBurdenByBracket = ref([
  { rate: 10, amount: 1160, percentage: 9.4, color: '#3b82f6' },
  { rate: 12, amount: 4266, percentage: 34.5, color: '#8b5cf6' },
  { rate: 22, amount: 6932, percentage: 56.1, color: '#ec4899' }
]);

const aiInsights = ref([
  {
    icon: DollarSign,
    title: 'Optimize Filing Status',
    description: 'Current status maximizes benefits based on your situation'
  },
  {
    icon: Target,
    title: 'Strategic Deductions',
    description: 'Maximize Section 80C investments before financial year end'
  },
  {
    icon: Zap,
    title: 'Quick Wins',
    description: '3 immediate actions could save you \u20B92,60,000'
  }
]);

const formatNumber = (num: number) => {
  return num.toLocaleString('en-IN');
};

// Real-time updates
let updateInterval: any;

onMounted(() => {
  updateInterval = setInterval(() => {
    lastUpdate.value = new Date().toLocaleTimeString();
  }, 5000);
});

onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval);
  }
});
</script>
