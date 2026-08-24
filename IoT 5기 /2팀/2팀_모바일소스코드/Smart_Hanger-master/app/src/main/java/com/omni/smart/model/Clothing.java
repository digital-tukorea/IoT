package com.omni.smart.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class Clothing {
    @SerializedName("id")
    private int id;

    @SerializedName("description")
    private String description;

    @SerializedName("category")
    private String category;

    @SerializedName("filepath")
    private String filepath;

    @SerializedName("download_url")
    private String downloadUrl;

    @SerializedName("yolo_labels")
    private List<String> yoloLabels;

    @SerializedName("summary")
    private String summary;

    @SerializedName("is_excluded")
    private boolean isExcluded;

    // 빨래 알림용
    @SerializedName("created_at")
    private double createdAt;

    public double getCreatedAt() { return createdAt; }
    public void setCreatedAt(double createdAt) { this.createdAt = createdAt; }

    public boolean isNeedsLaundry() {
        // 시연용: id가 1번인 옷은 무조건 7일 지난 것으로 처리
        if (id == 1) {
            return true;
        }

        long sevenDaysMillis = 7L * 24 * 60 * 60 * 1000;
        long createdAtMillis = (long) (createdAt * 1000); // 서버가 초 단위로 주므로 밀리초로 변환
        return (System.currentTimeMillis() - createdAtMillis) >= sevenDaysMillis;
    }

    public Clothing() {}

    public String getId() { return String.valueOf(id); }
    public void setId(String id) {
        try {
            this.id = Integer.parseInt(id);
        } catch (NumberFormatException e) {
            this.id = 0;
        }
    }

    public String getName() { return "Item #" + id; }
    public void setName(String name) { this.description = name; }

    public String getDescription() { return description; }

    public String getCategory() { return category != null ? category : "Clothing"; }
    public void setCategory(String category) { this.category = category; }

    public String getImageUrl() {
        return (downloadUrl != null && !downloadUrl.isEmpty()) ? downloadUrl : filepath;
    }
    public void setImageUrl(String imageUrl) { this.filepath = imageUrl; }

    public List<String> getYoloLabels() { return yoloLabels; }
    public void setYoloLabels(List<String> yoloLabels) { this.yoloLabels = yoloLabels; }

    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }

    public boolean isExcluded() { return isExcluded; }
    public void setExcluded(boolean excluded) { isExcluded = excluded; }
}