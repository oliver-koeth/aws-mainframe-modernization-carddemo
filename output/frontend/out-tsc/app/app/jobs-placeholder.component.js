import { AsyncPipe, NgIf } from "@angular/common";
import { Component, inject } from "@angular/core";
import { ApiClientService } from "./api-client.service";
import * as i0 from "@angular/core";
function JobsPlaceholderComponent_p_10_Template(rf, ctx) { if (rf & 1) {
    i0.ɵɵelementStart(0, "p");
    i0.ɵɵtext(1, " Connected to ");
    i0.ɵɵelementStart(2, "code");
    i0.ɵɵtext(3, "/api/jobs");
    i0.ɵɵelementEnd();
    i0.ɵɵtext(4, ". Current placeholder records: ");
    i0.ɵɵelementStart(5, "strong");
    i0.ɵɵtext(6);
    i0.ɵɵelementEnd()();
} if (rf & 2) {
    const jobs_r1 = ctx.ngIf;
    i0.ɵɵadvance(6);
    i0.ɵɵtextInterpolate(jobs_r1.length);
} }
export class JobsPlaceholderComponent {
    constructor() {
        this.apiClient = inject(ApiClientService);
        this.jobs$ = this.apiClient.listJobs();
    }
    static { this.ɵfac = function JobsPlaceholderComponent_Factory(__ngFactoryType__) { return new (__ngFactoryType__ || JobsPlaceholderComponent)(); }; }
    static { this.ɵcmp = /*@__PURE__*/ i0.ɵɵdefineComponent({ type: JobsPlaceholderComponent, selectors: [["app-jobs-placeholder"]], decls: 12, vars: 3, consts: [["aria-labelledby", "jobs-heading", 1, "jobs-card"], [1, "label"], ["id", "jobs-heading"], [1, "status-panel"], [1, "status-label"], [4, "ngIf"]], template: function JobsPlaceholderComponent_Template(rf, ctx) { if (rf & 1) {
            i0.ɵɵelementStart(0, "section", 0)(1, "p", 1);
            i0.ɵɵtext(2, "Batch Admin Surface");
            i0.ɵɵelementEnd();
            i0.ɵɵelementStart(3, "h2", 2);
            i0.ɵɵtext(4, "Jobs placeholder");
            i0.ɵɵelementEnd();
            i0.ɵɵelementStart(5, "p");
            i0.ɵɵtext(6, " This scaffold route reserves space for scheduled job monitoring and control in later modernization slices. ");
            i0.ɵɵelementEnd();
            i0.ɵɵelementStart(7, "div", 3)(8, "p", 4);
            i0.ɵɵtext(9, "Scaffold API");
            i0.ɵɵelementEnd();
            i0.ɵɵtemplate(10, JobsPlaceholderComponent_p_10_Template, 7, 1, "p", 5);
            i0.ɵɵpipe(11, "async");
            i0.ɵɵelementEnd()();
        } if (rf & 2) {
            i0.ɵɵadvance(10);
            i0.ɵɵproperty("ngIf", i0.ɵɵpipeBind1(11, 1, ctx.jobs$));
        } }, dependencies: [NgIf, AsyncPipe], styles: [".jobs-card[_ngcontent-%COMP%] {\n        background: #f5f7fa;\n        border: 1px solid #d8dee8;\n        border-radius: 1rem;\n        padding: 1.5rem;\n      }\n\n      .label[_ngcontent-%COMP%] {\n        color: #5b6470;\n        font-size: 0.8rem;\n        letter-spacing: 0.08em;\n        margin: 0 0 0.5rem;\n        text-transform: uppercase;\n      }\n\n      h2[_ngcontent-%COMP%] {\n        margin: 0 0 0.75rem;\n      }\n\n      p[_ngcontent-%COMP%] {\n        margin: 0;\n      }\n\n      .status-panel[_ngcontent-%COMP%] {\n        border-top: 1px solid #d8dee8;\n        margin-top: 1rem;\n        padding-top: 1rem;\n      }\n\n      .status-label[_ngcontent-%COMP%] {\n        color: #5b6470;\n        font-size: 0.75rem;\n        letter-spacing: 0.08em;\n        margin-bottom: 0.35rem;\n        text-transform: uppercase;\n      }\n\n      code[_ngcontent-%COMP%] {\n        background: #e8edf3;\n        border-radius: 0.25rem;\n        padding: 0.1rem 0.35rem;\n      }"] }); }
}
(() => { (typeof ngDevMode === "undefined" || ngDevMode) && i0.ɵsetClassMetadata(JobsPlaceholderComponent, [{
        type: Component,
        args: [{ selector: "app-jobs-placeholder", standalone: true, imports: [AsyncPipe, NgIf], template: `
    <section class="jobs-card" aria-labelledby="jobs-heading">
      <p class="label">Batch Admin Surface</p>
      <h2 id="jobs-heading">Jobs placeholder</h2>
      <p>
        This scaffold route reserves space for scheduled job monitoring and control in
        later modernization slices.
      </p>
      <div class="status-panel">
        <p class="status-label">Scaffold API</p>
        <p *ngIf="jobs$ | async as jobs">
          Connected to <code>/api/jobs</code>. Current placeholder records:
          <strong>{{ jobs.length }}</strong>
        </p>
      </div>
    </section>
  `, styles: ["\n      .jobs-card {\n        background: #f5f7fa;\n        border: 1px solid #d8dee8;\n        border-radius: 1rem;\n        padding: 1.5rem;\n      }\n\n      .label {\n        color: #5b6470;\n        font-size: 0.8rem;\n        letter-spacing: 0.08em;\n        margin: 0 0 0.5rem;\n        text-transform: uppercase;\n      }\n\n      h2 {\n        margin: 0 0 0.75rem;\n      }\n\n      p {\n        margin: 0;\n      }\n\n      .status-panel {\n        border-top: 1px solid #d8dee8;\n        margin-top: 1rem;\n        padding-top: 1rem;\n      }\n\n      .status-label {\n        color: #5b6470;\n        font-size: 0.75rem;\n        letter-spacing: 0.08em;\n        margin-bottom: 0.35rem;\n        text-transform: uppercase;\n      }\n\n      code {\n        background: #e8edf3;\n        border-radius: 0.25rem;\n        padding: 0.1rem 0.35rem;\n      }\n    "] }]
    }], null, null); })();
(() => { (typeof ngDevMode === "undefined" || ngDevMode) && i0.ɵsetClassDebugInfo(JobsPlaceholderComponent, { className: "JobsPlaceholderComponent", filePath: "src/app/jobs-placeholder.component.ts", lineNumber: 73 }); })();
