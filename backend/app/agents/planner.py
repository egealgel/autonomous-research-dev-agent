import uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session

from app.agents.claude import ClaudeResult, run_task_with_system
from app.agents.research import IngestedSource, ingest_url
from app.rag import SearchHit, search


class PlanType(StrEnum):
    software_roadmap = "software_roadmap"
    research_plan = "research_plan"
    prd = "prd"


SOFTWARE_ROADMAP_PROMPT = """You are a senior software architect with 15+ years of experience shipping production systems.
The user describes a project or goal. Produce a thorough, opinionated Markdown roadmap.

Write in the SAME language as the user's task. If CONTEXT excerpts are provided, ground your reasoning in them and cite sources inline as [n] referencing numbered blocks.

Required sections (use exactly these H2 headings):

## Özet / Summary
Tek paragraf — proje ne yapacak, kimin için, neden şimdi.

## Hedef ve Başarı Kriterleri
Ölçülebilir hedefler + somut kabul kriterleri (3-6 madde).

## Mimari Kararlar
Her kritik karar için: **Bağlam → Alternatifler → Öneri → Sebep → Risk**.
En az 3-5 önemli karar (örn. dil/framework seçimi, persistence, deploy, auth).

## Aşamalar (Milestones)
Numaralı liste. Her aşama: hedef, somut çıktılar (deliverables), tahmini süre, başarı kriteri.
3-5 aşamayı geçme; her biri 1-3 hafta aralığında olsun.

## Epic / Story Breakdown
Her aşama altında, story'leri tek tek listele. Her story:
- **Başlık**
- **Acceptance criteria** (3-5 madde, test edilebilir)
- **Tahmini efor** (S / M / L)
- **Bağımlılıklar** (varsa)

## Riskler ve Mitigasyon
Tablo: | Risk | Olasılık | Etki | Mitigasyon |. En az 4 satır.

## Açık Sorular
Senin kullanıcı olarak cevaplaman gereken sorular. Karar verilmeden ilerlenemeyecek olanları öncelikle yaz.

## Önerilen İlk Adım
Tek bir somut, küçük, bugün başlanabilir görev. Süre tahmini ile.

Disiplin kuralları:
- Spekülasyon yapma. Bilgin yoksa "Açık Sorular"a yaz.
- Genel tavsiyeler verme; bu projeye özel ol.
- Boş başlık yazma. Her bölüm gerçek değer üretmeli.
"""

RESEARCH_PLAN_PROMPT = """You are a research planner. The user wants to investigate a topic deeply.
Produce a Markdown research plan in the SAME language as the user's task. If CONTEXT excerpts are provided, cite them as [n].

Required sections:

## Konu ve Hipotez
1-2 paragraf — neyi öğrenmek istiyoruz, hangi temel hipotezi test ediyoruz.

## Anahtar Sorular (Öncelik Sırasıyla)
Öncelik sırasına göre numaralı liste (5-10 soru). Her sorunun yanına: neden kritik, hangi kararı bekleyen.

## Kaynak Haritası
Tablo: | Kaynak Tipi | Önerilen Kaynaklar (somut isim/URL) | Öncelik | Tahmini Süre |.
Tipler: akademik makaleler, kitaplar, blog/medium, GitHub repos, video/podcast, resmi dokümantasyon.
Spekülatif URL üretme; emin değilsen "ara: '<query>'" yaz.

## Okuma ve Çalışma Sırası
Sıralı liste — hangi kaynak hangi sıra ile, ne öğrenmek için. Her adımın net çıktısı olsun.

## Doğrulama Yöntemleri
Hipotezi nasıl test edeceksin: deney, prototip, mülakat, replikasyon, vs. Her birinin çıktısı ne olacak.

## Beklenen Bulgular ve Çıktı
- Hangi formatta raporlanacak (blog, internal doc, paper, demo)?
- Kim okuyacak?
- Karar verilirse hangi karar?

## Açık Sorular
Karar verilmeden plan başlatılamayacak sorular.

Disiplin:
- Yarı yarıya generic önerilerden kaçın.
- Süre tahminleri ekle (saat veya gün).
"""

PRD_PROMPT = """You are a senior product manager writing a technical PRD.
Produce a Markdown PRD in the SAME language as the user's task. If CONTEXT excerpts are provided, cite them as [n].

Required sections:

## Ürün Özeti
- One-liner: bu ürün ne yapıyor?
- Problem statement: hangi gerçek problemi, kimin için çözüyor?
- Çözüm hipotezi: neden bu yaklaşım?

## Kullanıcı Personas
2-4 persona. Her biri için: kim, hedef, sorun yaşadığı senaryo.

## User Stories
Format: **"As a [persona], I want [action], so that [outcome]"**. Öncelik (P0/P1/P2) ile etiketle.

## Kabul Kriterleri
Her P0 story için Given/When/Then formatında 3-5 senaryo.

## Edge Cases ve Hata Senaryoları
Her major flow için: ne yanlış gidebilir + sistem nasıl davranmalı.

## API / Data Model Taslakları
- Endpointler (method, path, request, response)
- Veri modelleri (alan adı, tip, kısıtlar)
- 3rd party entegrasyonlar

## Non-Functional Requirements
- Performans hedefleri (sayısal)
- Güvenlik / privacy gereksinimleri
- Ölçeklenebilirlik beklentileri (kullanıcı sayısı, RPS)
- Erişilebilirlik

## Out of Scope
Bu sürümde yapılmayacak şeyler, neden ertelendiği.

## Açık Sorular
Tasarım/karar bekleyen sorular.

Disiplin:
- Spekülatif metriklerden kaçın; "ölçülecek" ise belirt.
- Her acceptance criteria test edilebilir olmalı.
"""


_PROMPTS: dict[PlanType, str] = {
    PlanType.software_roadmap: SOFTWARE_ROADMAP_PROMPT,
    PlanType.research_plan: RESEARCH_PLAN_PROMPT,
    PlanType.prd: PRD_PROMPT,
}


@dataclass
class PlanOutcome:
    plan_type: PlanType
    sources: list[IngestedSource]
    hits: list[SearchHit]
    claude: ClaudeResult


def _build_context(hits: list[SearchHit]) -> str:
    blocks = [
        f"[{i}] source={hit.source_url} (type={hit.source_type}, sim={hit.similarity:.3f})\n{hit.content}"
        for i, hit in enumerate(hits, start=1)
    ]
    return "\n\n---\n\n".join(blocks)


def run_plan(
    db: Session,
    task_id: uuid.UUID,
    *,
    prompt: str,
    plan_type: PlanType,
    urls: list[str] | None = None,
    max_tokens: int = 6144,
) -> PlanOutcome:
    urls = urls or []
    sources: list[IngestedSource] = []
    hits: list[SearchHit] = []

    if urls:
        sources = [ingest_url(db, task_id, url) for url in urls]
        db.flush()
        hits = search(db, prompt, task_id=task_id, limit=8)

    if hits:
        context = _build_context(hits)
        user_message = f"CONTEXT:\n{context}\n\n---\nTASK:\n{prompt}"
    else:
        user_message = f"TASK:\n{prompt}"

    system = _PROMPTS[plan_type]
    claude = run_task_with_system(user_message, system=system, max_tokens=max_tokens)

    return PlanOutcome(plan_type=plan_type, sources=sources, hits=hits, claude=claude)
