import { Component } from "@angular/core";
import { RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";
import * as i0 from "@angular/core";
export class AppComponent {
    static { this.ɵfac = function AppComponent_Factory(__ngFactoryType__) { return new (__ngFactoryType__ || AppComponent)(); }; }
    static { this.ɵcmp = /*@__PURE__*/ i0.ɵɵdefineComponent({ type: AppComponent, selectors: [["app-root"]], decls: 11, vars: 0, consts: [[1, "shell"], [1, "shell-header"], [1, "eyebrow"], ["routerLink", "/jobs", "routerLinkActive", "active", 1, "nav-link"]], template: function AppComponent_Template(rf, ctx) { if (rf & 1) {
            i0.ɵɵelementStart(0, "main", 0)(1, "header", 1)(2, "p", 2);
            i0.ɵɵtext(3, "Phase 0");
            i0.ɵɵelementEnd();
            i0.ɵɵelementStart(4, "h1");
            i0.ɵɵtext(5, "CardDemo Modernization");
            i0.ɵɵelementEnd();
            i0.ɵɵelementStart(6, "p");
            i0.ɵɵtext(7, "Standalone Angular shell wiring is in place for later UI slices.");
            i0.ɵɵelementEnd();
            i0.ɵɵelementStart(8, "a", 3);
            i0.ɵɵtext(9, "Jobs");
            i0.ɵɵelementEnd()();
            i0.ɵɵelement(10, "router-outlet");
            i0.ɵɵelementEnd();
        } }, dependencies: [RouterLink, RouterLinkActive, RouterOutlet], styles: ["[_nghost-%COMP%] {\n        display: block;\n      }\n\n      .shell[_ngcontent-%COMP%] {\n        display: grid;\n        gap: 0.75rem;\n        margin: 0 auto;\n        max-width: 48rem;\n        padding: 3rem 1.5rem;\n      }\n\n      .eyebrow[_ngcontent-%COMP%] {\n        color: #6a6f7a;\n        font-size: 0.875rem;\n        letter-spacing: 0.08em;\n        margin: 0;\n        text-transform: uppercase;\n      }\n\n      h1[_ngcontent-%COMP%], \n   p[_ngcontent-%COMP%] {\n        margin: 0;\n      }\n\n      .shell-header[_ngcontent-%COMP%] {\n        display: grid;\n        gap: 1rem;\n      }\n\n      .nav-link[_ngcontent-%COMP%] {\n        border: 1px solid #c9d2de;\n        border-radius: 999px;\n        color: #183153;\n        justify-self: start;\n        padding: 0.5rem 0.9rem;\n        text-decoration: none;\n      }\n\n      .nav-link.active[_ngcontent-%COMP%] {\n        background: #183153;\n        border-color: #183153;\n        color: #fff;\n      }"] }); }
}
(() => { (typeof ngDevMode === "undefined" || ngDevMode) && i0.ɵsetClassMetadata(AppComponent, [{
        type: Component,
        args: [{ selector: "app-root", standalone: true, imports: [RouterLink, RouterLinkActive, RouterOutlet], template: "<main class=\"shell\">\n  <header class=\"shell-header\">\n    <p class=\"eyebrow\">Phase 0</p>\n    <h1>CardDemo Modernization</h1>\n    <p>Standalone Angular shell wiring is in place for later UI slices.</p>\n    <a routerLink=\"/jobs\" routerLinkActive=\"active\" class=\"nav-link\">Jobs</a>\n  </header>\n  <router-outlet></router-outlet>\n</main>\n", styles: ["\n      :host {\n        display: block;\n      }\n\n      .shell {\n        display: grid;\n        gap: 0.75rem;\n        margin: 0 auto;\n        max-width: 48rem;\n        padding: 3rem 1.5rem;\n      }\n\n      .eyebrow {\n        color: #6a6f7a;\n        font-size: 0.875rem;\n        letter-spacing: 0.08em;\n        margin: 0;\n        text-transform: uppercase;\n      }\n\n      h1,\n      p {\n        margin: 0;\n      }\n\n      .shell-header {\n        display: grid;\n        gap: 1rem;\n      }\n\n      .nav-link {\n        border: 1px solid #c9d2de;\n        border-radius: 999px;\n        color: #183153;\n        justify-self: start;\n        padding: 0.5rem 0.9rem;\n        text-decoration: none;\n      }\n\n      .nav-link.active {\n        background: #183153;\n        border-color: #183153;\n        color: #fff;\n      }\n    "] }]
    }], null, null); })();
(() => { (typeof ngDevMode === "undefined" || ngDevMode) && i0.ɵsetClassDebugInfo(AppComponent, { className: "AppComponent", filePath: "src/app/app.component.ts", lineNumber: 58 }); })();
