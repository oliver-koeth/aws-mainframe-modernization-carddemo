import { inject, Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import * as i0 from "@angular/core";
export class ApiClientService {
    constructor() {
        this.http = inject(HttpClient);
        this.basePath = "/api";
    }
    listJobs() {
        return this.getCollection("jobs");
    }
    listAccounts() {
        return this.getCollection("accounts");
    }
    listTransactions() {
        return this.getCollection("transactions");
    }
    getCollection(path) {
        return this.http.get(`${this.basePath}/${path}`);
    }
    static { this.ɵfac = function ApiClientService_Factory(__ngFactoryType__) { return new (__ngFactoryType__ || ApiClientService)(); }; }
    static { this.ɵprov = /*@__PURE__*/ i0.ɵɵdefineInjectable({ token: ApiClientService, factory: ApiClientService.ɵfac, providedIn: "root" }); }
}
(() => { (typeof ngDevMode === "undefined" || ngDevMode) && i0.ɵsetClassMetadata(ApiClientService, [{
        type: Injectable,
        args: [{
                providedIn: "root",
            }]
    }], null, null); })();
