<!-- frontend/src/App.vue -->
<script setup>
import TopNav from './components/layout/TopNav.vue';
</script>

<template>
  <TopNav />
  <main>
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </main>
</template>

<style scoped>
main {
  padding-top: 56px; /* height of TopNav */
  min-height: 100vh;
  background: var(--bg-page);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
