export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  public: {
    Tables: {
      streams: {
        Row: {
          id: string;
          slug: string;
          name: string;
          description: string | null;
          embed_url: string;
          source_url: string;
          platform: string | null;
          location_name: string | null;
          country_code: string | null;
          latitude: number | null;
          longitude: number | null;
          thumbnail_url: string | null;
          is_active: boolean;
          is_live: boolean;
          latest_detection_species: string | null;
          latest_detection_common_name: string | null;
          latest_detection_confidence: number | null;
          latest_detection_category: string | null;
          latest_detection_thumbnail_url: string | null;
          latest_detection_at: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          slug: string;
          name: string;
          description?: string | null;
          embed_url: string;
          source_url: string;
          platform?: string | null;
          location_name?: string | null;
          country_code?: string | null;
          latitude?: number | null;
          longitude?: number | null;
          thumbnail_url?: string | null;
          is_active?: boolean;
          is_live?: boolean;
          latest_detection_species?: string | null;
          latest_detection_common_name?: string | null;
          latest_detection_confidence?: number | null;
          latest_detection_category?: string | null;
          latest_detection_thumbnail_url?: string | null;
          latest_detection_at?: string | null;
        };
        Update: {
          id?: string;
          slug?: string;
          name?: string;
          description?: string | null;
          embed_url?: string;
          source_url?: string;
          platform?: string | null;
          location_name?: string | null;
          country_code?: string | null;
          latitude?: number | null;
          longitude?: number | null;
          thumbnail_url?: string | null;
          is_active?: boolean;
          is_live?: boolean;
          latest_detection_species?: string | null;
          latest_detection_common_name?: string | null;
          latest_detection_confidence?: number | null;
          latest_detection_category?: string | null;
          latest_detection_thumbnail_url?: string | null;
          latest_detection_at?: string | null;
        };
        Relationships: [];
      };
      detections: {
        Row: {
          id: string;
          stream_id: string;
          species_label: string | null;
          common_name: string | null;
          category: string;
          confidence: number;
          classification_confidence: number | null;
          prediction_source: string | null;
          bbox_x1: number | null;
          bbox_y1: number | null;
          bbox_x2: number | null;
          bbox_y2: number | null;
          thumbnail_path: string | null;
          inference_time_ms: number | null;
          detected_at: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          stream_id: string;
          species_label?: string | null;
          common_name?: string | null;
          category: string;
          confidence: number;
          classification_confidence?: number | null;
          prediction_source?: string | null;
          bbox_x1?: number | null;
          bbox_y1?: number | null;
          bbox_x2?: number | null;
          bbox_y2?: number | null;
          thumbnail_path?: string | null;
          inference_time_ms?: number | null;
          detected_at?: string;
        };
        Update: {
          id?: string;
          stream_id?: string;
          species_label?: string | null;
          common_name?: string | null;
          category?: string;
          confidence?: number;
          classification_confidence?: number | null;
          prediction_source?: string | null;
          bbox_x1?: number | null;
          bbox_y1?: number | null;
          bbox_x2?: number | null;
          bbox_y2?: number | null;
          thumbnail_path?: string | null;
          inference_time_ms?: number | null;
          detected_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "detections_stream_id_fkey";
            columns: ["stream_id"];
            isOneToOne: false;
            referencedRelation: "streams";
            referencedColumns: ["id"];
          },
        ];
      };
      stream_stats: {
        Row: {
          stream_id: string;
          stats: Json;
          computed_at: string;
        };
        Insert: {
          stream_id: string;
          stats: Json;
          computed_at?: string;
        };
        Update: {
          stream_id?: string;
          stats?: Json;
          computed_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "stream_stats_stream_id_fkey";
            columns: ["stream_id"];
            isOneToOne: true;
            referencedRelation: "streams";
            referencedColumns: ["id"];
          },
        ];
      };
      species_events: {
        Row: {
          id: string;
          stream_id: string;
          species_label: string;
          common_name: string;
          started_at: string;
          ended_at: string | null;
          peak_confidence: number | null;
          frame_count: number;
          best_thumbnail_path: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          stream_id: string;
          species_label: string;
          common_name: string;
          started_at: string;
          ended_at?: string | null;
          peak_confidence?: number | null;
          frame_count?: number;
          best_thumbnail_path?: string | null;
        };
        Update: {
          id?: string;
          stream_id?: string;
          species_label?: string;
          common_name?: string;
          started_at?: string;
          ended_at?: string | null;
          peak_confidence?: number | null;
          frame_count?: number;
          best_thumbnail_path?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "species_events_stream_id_fkey";
            columns: ["stream_id"];
            isOneToOne: false;
            referencedRelation: "streams";
            referencedColumns: ["id"];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
  };
};

export type Stream = Database["public"]["Tables"]["streams"]["Row"];
export type StreamInsert = Database["public"]["Tables"]["streams"]["Insert"];
export type Detection = Database["public"]["Tables"]["detections"]["Row"];
export type SpeciesEvent = Database["public"]["Tables"]["species_events"]["Row"];

export interface StreamStats {
  stream_id: string;
  stats: {
    [period: string]: {
      hourly: number[];
      total: number;
      species: { common_name: string; count: number; avg_confidence: number }[];
    };
  };
  computed_at: string;
}
