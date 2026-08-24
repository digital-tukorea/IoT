package com.omni.smart.adapter;

import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.DiffUtil;
import androidx.recyclerview.widget.ListAdapter;
import androidx.recyclerview.widget.RecyclerView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.load.engine.DiskCacheStrategy;
import com.omni.smart.databinding.ItemRecommendBinding;
import com.omni.smart.model.Clothing;
import com.omni.smart.util.ImageUtils;

public class RecommendAdapter extends ListAdapter<Clothing, RecommendAdapter.RecommendViewHolder> {

    private final OnRecommendClickListener listener;

    public interface OnRecommendClickListener {
        void onRecommendClick(Clothing clothing);
    }

    public RecommendAdapter(OnRecommendClickListener listener) {
        super(new DiffUtil.ItemCallback<Clothing>() {
            @Override
            public boolean areItemsTheSame(@NonNull Clothing oldItem, @NonNull Clothing newItem) {
                return oldItem.getId().equals(newItem.getId());
            }

            @Override
            public boolean areContentsTheSame(@NonNull Clothing oldItem, @NonNull Clothing newItem) {
                return oldItem.getName().equals(newItem.getName()) &&
                        oldItem.getImageUrl().equals(newItem.getImageUrl());
            }
        });
        this.listener = listener;
    }

    @NonNull
    @Override
    public RecommendViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemRecommendBinding binding = ItemRecommendBinding.inflate(LayoutInflater.from(parent.getContext()), parent, false);
        return new RecommendViewHolder(binding);
    }

    @Override
    public void onBindViewHolder(@NonNull RecommendViewHolder holder, int position) {
        holder.bind(getItem(position));
    }

    class RecommendViewHolder extends RecyclerView.ViewHolder {
        private final ItemRecommendBinding binding;

        public RecommendViewHolder(ItemRecommendBinding binding) {
            super(binding.getRoot());
            this.binding = binding;
        }

        public void bind(Clothing item) {
            if (item == null) return;

            binding.tvRecommendName.setText(item.getName());

            // Display YOLO labels as tags/categories
            StringBuilder labelsStr = new StringBuilder();
            if (item.getYoloLabels() != null && !item.getYoloLabels().isEmpty()) {
                for (String label : item.getYoloLabels()) {
                    labelsStr.append("#").append(label).append(" ");
                }
                binding.tvRecommendCategory.setText(labelsStr.toString().trim());
            } else {
                binding.tvRecommendCategory.setText(item.getCategory());
            }

            // 새로 추가: summary가 없으면 description(DB 상세 설명)으로 대체, 둘 다 없으면 기본 문구
            if (item.getSummary() != null && !item.getSummary().isEmpty()) {
                binding.tvRecommendReason.setText(item.getSummary());
            } else if (item.getDescription() != null && !item.getDescription().isEmpty()) {
                binding.tvRecommendReason.setText(item.getDescription());
            } else {
                binding.tvRecommendReason.setText("AI Recommended for today's weather");
            }

            String imageUrl = ImageUtils.getFullUrl(item.getImageUrl());
            if (imageUrl != null) {
                // 새로 추가: 캐시 무시하고 서버에서 항상 최신 이미지를 가져오도록 설정
                Glide.with(binding.ivRecommendImage.getContext())
                        .load(imageUrl)
                        .diskCacheStrategy(DiskCacheStrategy.NONE)
                        .skipMemoryCache(true)
                        .placeholder(com.omni.smart.R.drawable.placeholder)
                        .error(android.R.drawable.ic_menu_report_image)
                        .into(binding.ivRecommendImage);
            }

            binding.btnSelect.setOnClickListener(v -> listener.onRecommendClick(item));
        }
    }
}