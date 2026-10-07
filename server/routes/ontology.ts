import express from "express";
import { fullProvenanceChain, queryLedgerBySubject, verifyLedgerIntegrity } from "../ontology/ledger";
import { ONTOLOGY_VERSION } from "../ontology/model";

const router = express.Router();

router.get("/ontology", (_req, res) => {
  res.json({
    version: ONTOLOGY_VERSION,
    invariants: [
      "records_are_not_incidents",
      "event_correlation_is_separate_from_causation",
      "causation_is_separate_from_party_attribution",
      "case_opportunity_is_separate_from_contact_eligibility",
      "human_adjudication_never_overwrites_machine_output",
      "temporal_clocks_are_preserved_separately",
      "access_classification_is_separate_from_analytical_confidence"
    ]
  });
});

router.get("/ledger/integrity", (_req, res) => res.json({ valid: verifyLedgerIntegrity() }));
router.get("/ledger/subject/:subjectId", (req, res) => res.json(queryLedgerBySubject(req.params.subjectId)));
router.get("/ledger/provenance/:entryId", (req, res) => res.json(fullProvenanceChain(req.params.entryId)));

export default router;
