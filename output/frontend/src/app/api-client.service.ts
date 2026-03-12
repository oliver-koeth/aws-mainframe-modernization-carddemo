import { inject, Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";

@Injectable({
  providedIn: "root",
})
export class ApiClientService {
  private readonly http = inject(HttpClient);
  private readonly basePath = "/api";

  listJobs(): Observable<unknown[]> {
    return this.getCollection("jobs");
  }

  listAccounts(): Observable<unknown[]> {
    return this.getCollection("accounts");
  }

  listTransactions(): Observable<unknown[]> {
    return this.getCollection("transactions");
  }

  private getCollection(path: string): Observable<unknown[]> {
    return this.http.get<unknown[]>(`${this.basePath}/${path}`);
  }
}
