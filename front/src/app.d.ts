// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

// Svelte 5 runtime types
declare global {
	namespace svelte.JSX {
		interface HTMLAttributes<T> {
			onclick?: (event: MouseEvent) => void;
			onkeydown?: (event: KeyboardEvent) => void;
		}
	}
}

// Svelte 5 runtime declarations
declare global {
	function $props<T = any>(): T;
	function $state<T>(initial: T): T;
	function $effect(fn: () => void | (() => void)): void;
	function $derived<T>(fn: () => T): T;
	function $effect_root(fn: () => void | (() => void)): void;
}

import { type MathfieldElementAttributes } from "mathlive";

declare namespace svelteHTML {
	interface IntrinsicElements {
		'math-field': MathfieldElementAttributes;
	}
}

export {};