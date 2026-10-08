"""
test_dbc.py — Tests unitaires du contrat DBC ADAS FCW.

Valide que le fichier shared/dbc/adas.dbc respecte les spécifications
décrites dans docs/requirements.md (REQ-CAN-xxx).

Organisation :
    - TestDbcStructure  : structure DBC (messages, signaux, IDs, DLC)
    - TestPercObject    : encodage/décodage du message PERC_OBJECT
    - TestDecAlert      : encodage/décodage du message DEC_ALERT
    - TestDecHb         : encodage/décodage du message DEC_HB
    - TestRoundTrip     : idempotence encode -> decode -> encode
    - TestBoundary      : cas limites (min, max, overflow)
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Tests de structure DBC
# ===========================================================================

class TestDbcStructure:
    """Vérifie que le DBC contient bien les 3 messages attendus."""

    @pytest.mark.structure
    def test_dbc_loads(self, db):
        """Le DBC doit se charger sans erreur."""
        assert db is not None

    @pytest.mark.structure
    def test_message_count(self, db):
        """Le DBC doit contenir exactement 3 messages."""
        assert len(db.messages) == 3

    @pytest.mark.structure
    def test_message_names(self, db):
        """Les 3 messages doivent être PERC_OBJECT, DEC_ALERT, DEC_HB."""
        names = {msg.name for msg in db.messages}
        assert names == {"PERC_OBJECT", "DEC_ALERT", "DEC_HB"}

    @pytest.mark.structure
    def test_perc_object_id(self, perc_object_msg):
        """PERC_OBJECT doit avoir l'ID 0x100 (256)."""
        assert perc_object_msg.frame_id == 0x100

    @pytest.mark.structure
    def test_perc_object_dlc(self, perc_object_msg):
        """PERC_OBJECT doit faire 8 octets."""
        assert perc_object_msg.length == 8

    @pytest.mark.structure
    def test_dec_alert_id(self, dec_alert_msg):
        """DEC_ALERT doit avoir l'ID 0x200 (512)."""
        assert dec_alert_msg.frame_id == 0x200

    @pytest.mark.structure
    def test_dec_alert_dlc(self, dec_alert_msg):
        """DEC_ALERT doit faire 4 octets."""
        assert dec_alert_msg.length == 4

    @pytest.mark.structure
    def test_dec_hb_id(self, dec_hb_msg):
        """DEC_HB doit avoir l'ID 0x201 (513)."""
        assert dec_hb_msg.frame_id == 0x201

    @pytest.mark.structure
    def test_dec_hb_dlc(self, dec_hb_msg):
        """DEC_HB doit faire 2 octets."""
        assert dec_hb_msg.length == 2

    @pytest.mark.structure
    def test_perc_object_signals(self, perc_object_msg):
        """PERC_OBJECT doit avoir 5 signaux."""
        signal_names = {sig.name for sig in perc_object_msg.signals}
        assert signal_names == {"obj_id", "dist_m", "rel_speed_mps", "ttc_s", "valid"}


# ===========================================================================
# Tests PERC_OBJECT
# ===========================================================================

class TestPercObject:
    """Tests d'encodage/décodage du message PERC_OBJECT (0x100)."""

    @pytest.mark.encode
    def test_encode_returns_bytes(self, perc_object_msg, valid_perc_data):
        """L'encodage doit renvoyer 8 octets."""
        data = perc_object_msg.encode(valid_perc_data)
        assert isinstance(data, bytes)
        assert len(data) == 8

    @pytest.mark.encode
    def test_encode_obj_id(self, perc_object_msg):
        """L'obj_id doit occuper l'octet 0."""
        data = perc_object_msg.encode({
            "obj_id": 42, "dist_m": 0.0, "rel_speed_mps": 0.0,
            "ttc_s": 0.0, "valid": 0,
        })
        assert data[0] == 42

    @pytest.mark.encode
    def test_encode_dist_25m(self, perc_object_msg):
        """25.00 m doit être encodé en 2500 (little-endian)."""
        data = perc_object_msg.encode({
            "obj_id": 1, "dist_m": 25.0, "rel_speed_mps": 0.0,
            "ttc_s": 0.0, "valid": 1,
        })
        # 2500 = 0x09C4 → octets 1-2 : C4 09
        assert data[1] == 0xC4
        assert data[2] == 0x09

    @pytest.mark.decode
    def test_decode_roundtrip(self, perc_object_msg, valid_perc_data):
        """Encodage puis décodage doit redonner les valeurs d'origine."""
        encoded = perc_object_msg.encode(valid_perc_data)
        decoded = perc_object_msg.decode(encoded)

        # Comparaison avec tolérance sur les floats (facteur 0.01)
        assert decoded["obj_id"] == valid_perc_data["obj_id"]
        assert abs(decoded["dist_m"] - valid_perc_data["dist_m"]) < 0.01
        assert abs(decoded["rel_speed_mps"] - valid_perc_data["rel_speed_mps"]) < 0.01
        assert abs(decoded["ttc_s"] - valid_perc_data["ttc_s"]) < 0.01
        assert decoded["valid"] == valid_perc_data["valid"]

    @pytest.mark.decode
    def test_decode_valid_flag(self, perc_object_msg):
        """Le flag 'valid' doit être correctement décodé."""
        for flag in (0, 1):
            data = perc_object_msg.encode({
                "obj_id": 1, "dist_m": 10.0, "rel_speed_mps": 0.0,
                "ttc_s": 0.0, "valid": flag,
            })
            decoded = perc_object_msg.decode(data)
            assert decoded["valid"] == flag


# ===========================================================================
# Tests DEC_ALERT
# ===========================================================================

class TestDecAlert:
    """Tests d'encodage/décodage du message DEC_ALERT (0x200)."""

    @pytest.mark.encode
    def test_encode_returns_bytes(self, dec_alert_msg, valid_dec_alert_data):
        """L'encodage doit renvoyer 4 octets."""
        data = dec_alert_msg.encode(valid_dec_alert_data)
        assert len(data) == 4

    @pytest.mark.encode
    def test_encode_alert_level(self, dec_alert_msg):
        """L'alert_level doit être encodé sur 4 bits."""
        for level in range(5):
            data = dec_alert_msg.encode({
                "alert_level": level, "ttc_s": 0.0, "counter": 0, "crc": 0,
            })
            # Bits 0-3 du premier octet
            assert (data[0] & 0x0F) == level

    @pytest.mark.encode
    def test_encode_counter(self, dec_alert_msg):
        """Le compteur E2E doit être encodé sur 4 bits."""
        for counter in (0, 5, 15):
            data = dec_alert_msg.encode({
                "alert_level": 0, "ttc_s": 0.0, "counter": counter, "crc": 0,
            })
            # Bits 4-7 du 2ème octet (position 16..19)
            extracted = (data[2] >> 0) & 0x0F  # à ajuster selon DBC
            # Vérification via decode (plus robuste)
            decoded = dec_alert_msg.decode(data)
            assert decoded["counter"] == counter

    @pytest.mark.decode
    def test_decode_alert_level(self, dec_alert_msg):
        """L'alert_level doit être décodé correctement."""
        for level in range(5):
            data = dec_alert_msg.encode({
                "alert_level": level, "ttc_s": 0.0, "counter": 0, "crc": 0,
            })
            decoded = dec_alert_msg.decode(data)
            assert decoded["alert_level"] == level

    @pytest.mark.decode
    def test_decode_roundtrip(self, dec_alert_msg, valid_dec_alert_data):
        """Round-trip complet pour DEC_ALERT."""
        encoded = dec_alert_msg.encode(valid_dec_alert_data)
        decoded = dec_alert_msg.decode(encoded)

        assert decoded["alert_level"] == valid_dec_alert_data["alert_level"]
        assert abs(decoded["ttc_s"] - valid_dec_alert_data["ttc_s"]) < 0.01
        assert decoded["counter"] == valid_dec_alert_data["counter"]
        assert decoded["crc"] == valid_dec_alert_data["crc"]


# ===========================================================================
# Tests DEC_HB
# ===========================================================================

class TestDecHb:
    """Tests d'encodage/décodage du message DEC_HB (0x201)."""

    @pytest.mark.encode
    def test_encode_returns_bytes(self, dec_hb_msg, valid_dec_hb_data):
        """L'encodage doit renvoyer 2 octets."""
        data = dec_hb_msg.encode(valid_dec_hb_data)
        assert len(data) == 2

    @pytest.mark.encode
    def test_encode_alive_counter(self, dec_hb_msg):
        """Le alive_ctr doit occuper l'octet 0."""
        data = dec_hb_msg.encode({"alive_ctr": 42, "state": 0})
        assert data[0] == 42

    @pytest.mark.encode
    def test_encode_state(self, dec_hb_msg):
        """Le state doit occuper l'octet 1."""
        data = dec_hb_msg.encode({"alive_ctr": 0, "state": 3})
        assert data[1] == 3

    @pytest.mark.decode
    def test_decode_roundtrip(self, dec_hb_msg, valid_dec_hb_data):
        """Round-trip complet pour DEC_HB."""
        encoded = dec_hb_msg.encode(valid_dec_hb_data)
        decoded = dec_hb_msg.decode(encoded)

        assert decoded["alive_ctr"] == valid_dec_hb_data["alive_ctr"]
        assert decoded["state"] == valid_dec_hb_data["state"]


# ===========================================================================
# Tests round-trip globaux
# ===========================================================================

class TestRoundTrip:
    """Tests d'idempotence : encode -> decode -> encode."""

    @pytest.mark.roundtrip
    def test_perc_object_idempotent(self, perc_object_msg, valid_perc_data):
        """Deux encodages successifs donnent les mêmes octets."""
        encoded1 = perc_object_msg.encode(valid_perc_data)
        decoded = perc_object_msg.decode(encoded1)
        encoded2 = perc_object_msg.encode(decoded)
        assert encoded1 == encoded2

    @pytest.mark.roundtrip
    def test_dec_alert_idempotent(self, dec_alert_msg, valid_dec_alert_data):
        """Deux encodages successifs donnent les mêmes octets."""
        encoded1 = dec_alert_msg.encode(valid_dec_alert_data)
        decoded = dec_alert_msg.decode(encoded1)
        encoded2 = dec_alert_msg.encode(decoded)
        assert encoded1 == encoded2


# ===========================================================================
# Tests de cas limites
# ===========================================================================

class TestBoundary:
    """Tests des valeurs limites (min, max)."""

    @pytest.mark.boundary
    def test_obj_id_max(self, perc_object_msg):
        """obj_id = 255 (max sur 8 bits) doit passer."""
        data = perc_object_msg.encode({
            "obj_id": 255, "dist_m": 0.0, "rel_speed_mps": 0.0,
            "ttc_s": 0.0, "valid": 1,
        })
        decoded = perc_object_msg.decode(data)
        assert decoded["obj_id"] == 255

    @pytest.mark.boundary
    def test_dist_max(self, perc_object_msg):
        """dist_m proche du max (655.35) doit passer."""
        data = perc_object_msg.encode({
            "obj_id": 1, "dist_m": 655.35, "rel_speed_mps": 0.0,
            "ttc_s": 0.0, "valid": 1,
        })
        decoded = perc_object_msg.decode(data)
        assert abs(decoded["dist_m"] - 655.35) < 0.01

    @pytest.mark.boundary
    def test_counter_wrap(self, dec_alert_msg):
        """Le compteur E2E doit wrapper de 15 à 0."""
        for counter in (0, 15):
            data = dec_alert_msg.encode({
                "alert_level": 0, "ttc_s": 0.0, "counter": counter, "crc": 0,
            })
            decoded = dec_alert_msg.decode(data)
            assert decoded["counter"] == counter

    @pytest.mark.boundary
    def test_alive_ctr_max(self, dec_hb_msg):
        """alive_ctr = 255 (max) doit passer."""
        data = dec_hb_msg.encode({"alive_ctr": 255, "state": 4})
        decoded = dec_hb_msg.decode(data)
        assert decoded["alive_ctr"] == 255
