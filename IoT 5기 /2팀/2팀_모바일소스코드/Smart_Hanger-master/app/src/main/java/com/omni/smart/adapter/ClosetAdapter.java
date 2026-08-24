package com.omni.smart.adapter;

import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.load.engine.DiskCacheStrategy;
import com.omni.smart.databinding.ItemClosetBinding;
import com.omni.smart.model.Clothing;
import com.omni.smart.util.ImageUtils;

import java.util.ArrayList;
import java.util.List;

public class ClosetAdapter extends RecyclerView.Adapter<ClosetAdapter.ClosetViewHolder> {
    private List<Clothing> clothingList = new ArrayList<>();
    private final OnClosetClickListener listener;

    public interface OnClosetClickListener {
        void onClosetItemClick(Clothing clothing);
    }

    public ClosetAdapter(OnClosetClickListener listener) {
        this.listener = listener;
    }

    public void setClothingList(List<Clothing> list) {
        this.clothingList = list;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public ClosetViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemClosetBinding binding = ItemClosetBinding.inflate(LayoutInflater.from(parent.getContext()), parent, false);
        return new ClosetViewHolder(binding);
    }

    @Override
    public void onBindViewHolder(@NonNull ClosetViewHolder holder, int position) {
        holder.bind(clothingList.get(position), listener);
    }

    @Override
    public int getItemCount() {
        return clothingList.size();
    }

    static class ClosetViewHolder extends RecyclerView.ViewHolder {
        private ItemClosetBinding binding;

        public ClosetViewHolder(ItemClosetBinding binding) {
            super(binding.getRoot());
            this.binding = binding;
        }

        public void bind(Clothing item, OnClosetClickListener listener) {
            binding.tvClothName.setText("Item #" + item.getId());
            binding.cbExclude.setChecked(item.isExcluded());

            String imageUrl = ImageUtils.getFullUrl(item.getImageUrl());
            if (imageUrl != null) {
                // 새로 추가: 캐시 무시하고 서버에서 항상 최신 이미지를 가져오도록 설정
                Glide.with(binding.ivClothImage.getContext())
                        .load(imageUrl)
                        .diskCacheStrategy(DiskCacheStrategy.NONE)
                        .skipMemoryCache(true)
                        .placeholder(com.omni.smart.R.drawable.placeholder)
                        .error(android.R.drawable.ic_menu_report_image)
                        .into(binding.ivClothImage);
            }

            binding.cbExclude.setOnCheckedChangeListener((buttonView, isChecked) -> {
                item.setExcluded(isChecked);
            });

            binding.getRoot().setOnClickListener(v -> {
                if (listener != null) {
                    listener.onClosetItemClick(item);
                }
            });
        }
    }
}